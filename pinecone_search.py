import os
import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone

# Configure logging
logger = logging.getLogger(__name__)


class PineconeSearchService:
    """
    Service class for searching Pinecone vector database.
    Handles initialization and text-based search operations.
    """
    
    def __init__(self, api_key: Optional[str] = None, index_name: Optional[str] = None):
        """
        Initialize the Pinecone search service.
        
        Args:
            api_key: Pinecone API key (defaults to PINECONE_API_KEY env var)
            index_name: Pinecone index name (defaults to PINECONE_INDEX_NAME env var)
        """
        self.api_key = api_key or os.environ.get("PINECONE_API_KEY")
        self.index_name = index_name or os.environ.get("PINECONE_INDEX_NAME")
        self.pc = None
        self.index = None
        self._initialized = False
        
    def _initialize(self):
        """Lazy initialization of Pinecone client and index."""
        if not self._initialized:
            logger.info("Initializing Pinecone...")
            self.pc = Pinecone(api_key=self.api_key)
            self.index = self.pc.Index(self.index_name)
            self._initialized = True
            logger.info(f"Pinecone index '{self.index_name}' initialized")
    
    def search(self, query_text: str, intent_data: Optional[Dict[str, Any]] = None, top_k: int = 10) -> List[Any]:
        """
        Search Pinecone using text input with optional metadata filters.
        
        Args:
            query_text: The search query text
            intent_data: Optional dictionary containing category and attributes for filtering
            top_k: Maximum number of results to return
            
        Returns:
            List of match objects with id, score, and metadata attributes
        """
        # Ensure client is initialized
        self._initialize()
        
        # Validate query_text is not empty
        if not query_text or not query_text.strip():
            logger.error("Query text is empty or contains only whitespace")
            return []
        
        logger.info(f"Searching Pinecone with text: '{query_text}', top_k={top_k}")
        
        # Build metadata filter from intent_data
        filter_dict = self._build_filter(intent_data) if intent_data else {}
        
        try:
            logger.info(f"Applying filters: {filter_dict}")
            
            # Prepare query parameters
            query_params = {
                "inputs": {"text": query_text},
                "top_k": top_k
            }
            
            # Note: Uncomment below to enable filtering when needed
            # if filter_dict:
            #     query_params["filter"] = filter_dict
            
            # Execute search
            results = self.index.search(
                namespace="__default__", 
                query=query_params,
                fields=["*"]  # Request all metadata fields
            )
            
            # Extract and convert hits to match objects
            converted_matches = self._convert_results_to_matches(results)
            logger.info(f"Found {len(converted_matches)} matches")
            
            return converted_matches
            
        except Exception as e:
            logger.error(f"Pinecone search error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _build_filter(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Pinecone metadata filter from intent data.
        
        Args:
            intent_data: Dictionary containing category, subcategory and attributes
            
        Returns:
            Dictionary with Pinecone filter conditions
        """
        filter_dict = {}
        
        category = intent_data.get('category')
        subcategory = intent_data.get('subcategory')
        attributes = intent_data.get('attributes', {})
        
        # Category filter
        if category:
            filter_dict['category'] = {"$eq": category}
        
        # Subcategory filter (more specific)
        if subcategory:
            filter_dict['subcategory'] = {"$eq": subcategory}
        
        # Attribute filters
        if attributes.get('color'):
            filter_dict['color'] = {"$eq": attributes['color']}
        
        if attributes.get('fabric'):
            filter_dict['fabric'] = {"$eq": attributes['fabric']}
        
        if attributes.get('technique'):
            filter_dict['technique'] = {"$eq": attributes['technique']}
        
        if attributes.get('pattern'):
            filter_dict['pattern'] = {"$eq": attributes['pattern']}
        
        # Filter for in-stock items (boolean True, not string)
        # Commenting out for now as it might need adjustment based on your data
        # filter_dict['in_stock'] = {"$eq": True}
        
        # Price range filter
        price_range = attributes.get('price_range')
        if price_range:
            if isinstance(price_range, dict):
                if price_range.get('min'):
                    filter_dict['price'] = {"$gte": price_range['min']}
                if price_range.get('max'):
                    if 'price' in filter_dict:
                        filter_dict['price']['$lte'] = price_range['max']
                    else:
                        filter_dict['price'] = {"$lte": price_range['max']}
        
        return filter_dict
    
    def _convert_results_to_matches(self, results: Any) -> List[Any]:
        """
        Convert Pinecone search results to match objects.
        
        Args:
            results: Raw results from Pinecone search
            
        Returns:
            List of match objects with id, score, and metadata
        """
        converted_matches = []
        
        if results and hasattr(results, 'result') and results.result:
            hits = results.result.get('hits', [])
            
            for hit in hits:
                # Create a match-like object for backward compatibility
                match_obj = type('Match', (), {
                    'id': hit.get('_id'),
                    'score': hit.get('_score', 0),
                    'metadata': hit.get('fields', {})
                })()
                converted_matches.append(match_obj)
        else:
            logger.warning("No results returned from search")
        
        return converted_matches
