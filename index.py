from http.server import BaseHTTPRequestHandler
import json
import os
import logging
from dotenv import load_dotenv
from .text_processor import TextProcessor
from .pinecone_search import PineconeSearchService
from .bot_service import BotService

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot service (singleton pattern)
bot_service = None


class handler(BaseHTTPRequestHandler):
    # Mode selection: 'bot', 'pinecone', or 'text'
    MODE = 'bot'  # Set to 'bot' to use BotService (recommended), 'pinecone' for direct search, 'text' for TextProcessor

    def do_POST(self):
        global bot_service
        logger.info("Received POST request")
        
        # Get the content length and read the body
        content_length = int(self.headers['Content-Length'])
        logger.debug(f"Content length: {content_length}")
        post_data = self.rfile.read(content_length)
        
        try:
            # Parse JSON data
            logger.info(f"Raw post data: {post_data}")
            data = json.loads(post_data.decode('utf-8'))
            logger.info(f"Parsed JSON data: {data}")
            logger.info(f"Available keys in data: {list(data.keys())}")
            
            # Support both 'text' and 'message' keys
            user_text = data.get('text') or data.get('message', '')
            session_id = data.get('session_id', 'default')
            logger.info(f"Extracted text: '{user_text}', Session: {session_id}, Text length: {len(user_text)}")
            
            # Validate that text is not empty
            if not user_text or not user_text.strip():
                logger.error("Received empty or whitespace-only text")
                raise ValueError("Text input cannot be empty")
            
            if self.MODE == 'bot':
                logger.info("Using BotService")
                # Initialize bot service if not already initialized
                if bot_service is None:
                    openai_key = os.environ.get("OPENAI_API_KEY")
                    pinecone_key = os.environ.get("PINECONE_API_KEY")
                    pinecone_index = os.environ.get("PINECONE_INDEX_NAME")
                    
                    if not openai_key:
                        logger.error("OPENAI_API_KEY not found in environment variables")
                        raise ValueError("OPENAI_API_KEY must be set in environment variables")
                    
                    bot_service = BotService(
                        openai_api_key=openai_key,
                        pinecone_api_key=pinecone_key,
                        pinecone_index_name=pinecone_index
                    )
                    logger.info("BotService initialized successfully")
                
                # Process message through bot service
                response_data = bot_service.process_message(user_text, session_id)
                
                result = response_data.get('response', '')
                product_list = response_data.get('products', [])
                action = response_data.get('action', 'unknown')
                
                logger.info(f"Bot response generated. Action: {action}, Products: {len(product_list)}")
                
            elif self.MODE == 'pinecone':
                logger.info("Using Pinecone search service directly")
                # Use Pinecone search service
                api_key = os.environ.get("PINECONE_API_KEY")
                index_name = os.environ.get("PINECONE_INDEX_NAME")
                logger.debug(f"Initializing Pinecone with index: {index_name}")
                search_service = PineconeSearchService(api_key=api_key, index_name=index_name)
                
                # Search with the user's text
                logger.info(f"Searching Pinecone with query: '{user_text[:50]}...'")
                results = search_service.search(query_text=user_text, top_k=5)
                logger.info(f"Search completed. Found {len(results) if results else 0} results")
                
                # Format results for frontend
                if results:
                    # Create a message for the user
                    result_message = f"I found {len(results)} products for you:"
                    
                    # Convert results to product objects for the UI
                    products = []
                    for match in results:
                        product = {
                            'name': match.metadata.get('product_name', 'Unknown'),
                            'price': match.metadata.get('price', 'N/A'),
                            'category': match.metadata.get('category', ''),
                            'color': match.metadata.get('color', ''),
                            'fabric': match.metadata.get('fabric', ''),
                            'technique': match.metadata.get('technique', ''),
                            'pattern': match.metadata.get('pattern', ''),
                            'description': match.metadata.get('description', ''),
                            'in_stock': match.metadata.get('in_stock', 'yes'),
                            'colors_available': match.metadata.get('colors_available', ''),
                            'score': round(match.score, 4)
                        }
                        products.append(product)
                    
                    result = result_message
                    product_list = products
                else:
                    result = "Sorry, I couldn't find any products matching your search."
                    product_list = []
                    logger.warning("No results found in Pinecone search")
            else:  # text mode
                logger.info("Using TextProcessor")
                # Process text using TextProcessor class
                processor = TextProcessor()
                result = processor.process_text(user_text)
                product_list = []
                logger.info("Text processing completed")
            
            # Return JSON response in the format expected by frontend
            logger.info("Sending successful response")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'response': result,  # Changed from 'message' to 'response'
                'products': product_list  # Add products array
            }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
            logger.debug("Response sent successfully")
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                'error': str(e)
            }
            
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
            logger.debug("Error response sent")
        
        return
    
    def do_OPTIONS(self):
        # Handle preflight CORS request
        logger.info("Received OPTIONS request (CORS preflight)")
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        logger.debug("CORS preflight response sent")
        return
