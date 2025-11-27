"""
Bot Service - Jhimki Stock Assistant AI orchestrator for handcrafted fashion boutique

This service acts as the Jhimki Stock Assistant, handling:
- Intent understanding using GPT (extracting customer product requests)
- Action decisions (search products from Pinecone, clarify intent, or general chat)
- Conversation session management with context
- Response generation with natural language following Jhimki brand voice
- Product data formatting and presentation from vector database
- Integration with Pinecone search service for product retrieval

Key Features:
- Only suggests products retrieved from Pinecone database (no hallucinations)
- Filters by category, fabric, technique, color, pattern, price, and stock
- Maintains warm, customer-friendly tone for Indian handcrafted fashion
- Handles off-topic queries gracefully
- Prioritizes in-stock items

Usage:
    bot = BotService()
    response = bot.process_message("Do you have indigo ajrakh cotton saree under 3000?", session_id="user123")
    # Returns: {"response": "...", "products": [...], "action": "search"}
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
from openai import OpenAI
from .pinecone_search import PineconeSearchService

# Configure logging
logger = logging.getLogger(__name__)


class ConversationSession:
    """
    Manages a single conversation session with context and history.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.messages: List[Dict[str, str]] = []
        self.context: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_updated = datetime.now()
    
    def get_context_window(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent messages for context (excluding timestamps)."""
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [{"role": msg["role"], "content": msg["content"]} for msg in recent]
    
    def update_context(self, key: str, value: Any):
        """Update session context (e.g., extracted preferences, filters)."""
        self.context[key] = value
        self.last_updated = datetime.now()


class BotService:
    """
    Bot Brain Service that orchestrates:
    - Intent understanding (GPT-based)
    - Action decisions (search/clarify/chat)
    - Conversation management
    - Response generation with or without products
    - Product data formatting
    - Search service integration
    """
    
    # Action types
    ACTION_SEARCH = "search"
    ACTION_CLARIFY = "clarify"
    ACTION_CHAT = "chat"
    
    def __init__(self, openai_api_key: Optional[str] = None, 
                 pinecone_api_key: Optional[str] = None,
                 pinecone_index_name: Optional[str] = None):
        """
        Initialize the bot service.
        
        Args:
            openai_api_key: OpenAI API key for GPT
            pinecone_api_key: Pinecone API key for search
            pinecone_index_name: Pinecone index name
        """
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        # Initialize search service
        self.search_service = PineconeSearchService(
            api_key=pinecone_api_key,
            index_name=pinecone_index_name
        )
        
        # In-memory session store (can be replaced with Redis/DB)
        self.sessions: Dict[str, ConversationSession] = {}
        
        logger.info("BotService initialized")
    
    def get_or_create_session(self, session_id: str) -> ConversationSession:
        """Get existing session or create a new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationSession(session_id)
            logger.info(f"Created new session: {session_id}")
        return self.sessions[session_id]
    
    def process_message(self, user_message: str, session_id: str = "default") -> Dict[str, Any]:
        """
        Main entry point: Process a user message and return a response.
        
        Args:
            user_message: The user's input text
            session_id: Unique session identifier
            
        Returns:
            Dictionary with response, products (if any), and metadata
        """
        try:
            # Get or create session
            session = self.get_or_create_session(session_id)
            
            # Add user message to history
            session.add_message("user", user_message)
            
            # Step 1: Understand intent
            intent = self._extract_intent(user_message, session)
            logger.info(f"Extracted intent: {intent}")
            
            # Step 2: Decide action
            action = self._decide_action(intent, session)
            logger.info(f"Decided action: {action}")
            
            # Step 3: Execute action and generate response
            response_data = self._execute_action(action, intent, user_message, session)
            
            # Step 4: Add assistant response to history
            session.add_message("assistant", response_data["response"])
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "products": [],
                "action": "error",
                "error": str(e)
            }
    
    def _extract_intent(self, user_message: str, session: ConversationSession) -> Dict[str, Any]:
        """
        Use GPT to extract user intent from the message.
        
        Returns:
            Dictionary containing:
            - intent_type: product_search, general_question, greeting, etc.
            - category: clothing category if applicable
            - attributes: extracted attributes (color, fabric, etc.)
            - search_query: reformulated search query
            - confidence: confidence score
        """
        # Build context from conversation history
        context_messages = session.get_context_window(max_messages=5)
        
        # System prompt for intent extraction
        system_prompt = """You are the Jhimki Stock Assistant, an AI agent for a small handcrafted fashion boutique specializing in Indian ethnic wear.

Your job is to understand user intent and extract relevant information for product search from our fixed catalogue.

Product Categories: Saree, Suit Set, Fabric, Dupatta, Stole
Subcategories: Chanderi Saree, Ajrakh Saree, Khadi Saree, Chanderi Suit, Ajrakh Suit, Khadi Suit, Ajrakh Fabric, Maheshwari
Fabrics: Silk Cotton, Cotton, Chanderi, Khadi Cotton, Modal Silk, Modal, Indigo Cotton
Techniques: Handwoven, Ajrakh Block Print, Ajrakh Print, Ajrakh Natural Dye
Common Colors: Pistachio, Teal, Steel Grey, Rust, Maroon, Emerald, Pastel Pink, Sand Beige, Rose, Off White, Sky Blue, Indigo, Pink
Patterns: Geometric, Textured, Floral, Stripes, Panel, Buta, Paisley, Solid, Ajrakh Blocks

Analyze the user's message and return a JSON object with:
{
  "intent_type": "product_search" | "general_question" | "greeting" | "clarification_needed" | "off_topic",
  "category": "Saree" | "Suit Set" | "Fabric" | "Dupatta" | "Stole" | null,
  "subcategory": "specific subcategory or null",
  "attributes": {
    "color": "color value or null",
    "fabric": "fabric type or null",
    "technique": "technique or null",
    "pattern": "pattern or null",
    "price_range": "budget info or null",
    "price_min": "minimum price number or null",
    "price_max": "maximum price number or null"
  },
  "search_query": "refined search query text",
  "confidence": 0.0-1.0,
  "needs_clarification": true/false,
  "clarification_question": "question to ask user if needed"
}

Examples:
- "Do you have indigo ajrakh cotton saree under 3000?" -> intent_type: "product_search", category: "Saree", subcategory: "Ajrakh Saree", attributes: {color: "indigo", fabric: "cotton", technique: "ajrakh", price_max: "3000"}
- "Show me maheshwari silk in pink" -> intent_type: "product_search", subcategory: "Maheshwari", attributes: {fabric: "silk", color: "pink"}
- "Ajrakh suit set in modal, budget 3-4k" -> intent_type: "product_search", category: "Suit Set", subcategory: "Ajrakh Suit", attributes: {fabric: "modal", price_min: "3000", price_max: "4000"}
- "Hello" -> intent_type: "greeting"
- "What's the weather?" -> intent_type: "off_topic"
- "Tell me about fabrics" -> intent_type: "general_question"

Remember: You only help with Jhimki's product catalogue. Mark unrelated queries as "off_topic".
"""
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        messages.extend(context_messages)
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Call GPT for intent extraction
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            intent_json = response.choices[0].message.content
            intent = json.loads(intent_json)
            
            # Store extracted attributes in session context
            if intent.get("attributes"):
                session.update_context("last_attributes", intent["attributes"])
            if intent.get("category"):
                session.update_context("last_category", intent["category"])
            
            return intent
            
        except Exception as e:
            logger.error(f"Error extracting intent: {str(e)}", exc_info=True)
            # Return a default intent
            return {
                "intent_type": "general_question",
                "search_query": user_message,
                "confidence": 0.5,
                "needs_clarification": False
            }
    
    def _decide_action(self, intent: Dict[str, Any], session: ConversationSession) -> str:
        """
        Decide what action to take based on intent.
        
        Returns:
            ACTION_SEARCH, ACTION_CLARIFY, or ACTION_CHAT
        """
        intent_type = intent.get("intent_type", "general_question")
        needs_clarification = intent.get("needs_clarification", False)
        confidence = intent.get("confidence", 0.5)
        
        # If it's an off-topic query, handle it as chat
        if intent_type == "off_topic":
            return self.ACTION_CHAT
        
        # If clarification is needed or confidence is low
        if needs_clarification or confidence < 0.6:
            return self.ACTION_CLARIFY
        
        # If it's a product search intent
        if intent_type == "product_search":
            return self.ACTION_SEARCH
        
        # For greetings and general questions
        return self.ACTION_CHAT
    
    def _execute_action(self, action: str, intent: Dict[str, Any], 
                       user_message: str, session: ConversationSession) -> Dict[str, Any]:
        """
        Execute the decided action and return formatted response.
        """
        if action == self.ACTION_SEARCH:
            return self._execute_search(intent, session)
        elif action == self.ACTION_CLARIFY:
            return self._execute_clarify(intent, session)
        else:  # ACTION_CHAT
            return self._execute_chat(intent, user_message, session)
    
    def _execute_search(self, intent: Dict[str, Any], session: ConversationSession) -> Dict[str, Any]:
        """
        Execute product search using the search service.
        """
        search_query = intent.get("search_query", "")
        intent_data = {
            "category": intent.get("category"),
            "subcategory": intent.get("subcategory"),
            "attributes": intent.get("attributes", {})
        }
        
        logger.info(f"Executing search with query: '{search_query}'")
        
        # Call Pinecone search service
        matches = self.search_service.search(
            query_text=search_query,
            intent_data=intent_data,
            top_k=10
        )
        
        # Format products
        products = self._format_products(matches)
        
        # Generate contextual response message
        response_message = self._generate_search_response(intent, products, session)
        
        return {
            "response": response_message,
            "products": products,
            "action": self.ACTION_SEARCH,
            "intent": intent
        }
    
    def _execute_clarify(self, intent: Dict[str, Any], session: ConversationSession) -> Dict[str, Any]:
        """
        Ask for clarification when intent is unclear.
        """
        # Use the clarification question from intent if available
        clarification = intent.get("clarification_question")
        
        if not clarification:
            # Generate a generic clarification
            clarification = "I want to help you find the perfect item! Could you provide more details about what you're looking for? For example, the type of clothing, color, fabric, or occasion?"
        
        return {
            "response": clarification,
            "products": [],
            "action": self.ACTION_CLARIFY,
            "intent": intent
        }
    
    def _execute_chat(self, intent: Dict[str, Any], user_message: str, 
                     session: ConversationSession) -> Dict[str, Any]:
        """
        Handle general chat (greetings, questions, etc.) without product search.
        """
        context_messages = session.get_context_window(max_messages=5)
        
        system_prompt = """You are the Jhimki Stock Assistant, an AI agent for a small handcrafted fashion boutique.

Your role:
- Greet customers warmly and professionally
- Answer questions about product categories, fabrics, techniques, and the Jhimki brand
- Guide customers toward searching our catalogue
- Maintain a warm, concise, customer-friendly tone aligned with an Indian handcrafted fashion brand

Available product categories: Sarees, Suit Sets, Fabrics, Dupattas, Stoles
Available fabrics: Cotton, Silk Cotton, Chanderi, Modal Silk, Modal, Khadi Cotton, Indigo Cotton
Available techniques: Handwoven, Ajrakh Block Print, Ajrakh Natural Dye

STRICT RULES:
- DO NOT answer questions unrelated to Jhimki's products or Indian handcrafted fashion
- If asked about something off-topic (weather, news, general knowledge), politely say: "I'm only able to help with Jhimki's product catalogue and availability. How can I help you find something today?"
- Keep responses short (2-3 sentences maximum)
- Encourage customers to ask about specific products

Examples:
User: "Hello!"
You: "Welcome to Jhimki! 🙏 We specialize in handcrafted sarees, suit sets, and fabrics featuring traditional techniques like Ajrakh and Chanderi. What can I help you find today?"

User: "What fabrics do you have?"
You: "We work with beautiful natural fabrics like Cotton, Silk Cotton, Chanderi, Modal, and Khadi Cotton. Many pieces feature Ajrakh block printing and natural dyeing. Would you like to see something in a particular fabric?"

User: "What's the weather today?"
You: "I'm only able to help with Jhimki's product catalogue and availability. How can I help you find something today?"
"""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        messages.extend(context_messages)
        messages.append({"role": "user", "content": user_message})
        
        # Check if it's an off-topic query
        intent_type = intent.get("intent_type", "general_question")
        if intent_type == "off_topic":
            return {
                "response": "I'm only able to help with Jhimki's product catalogue and availability. How can I help you find something from our collection today?",
                "products": [],
                "action": self.ACTION_CHAT,
                "intent": intent
            }
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=150
            )
            
            chat_response = response.choices[0].message.content
            
            return {
                "response": chat_response,
                "products": [],
                "action": self.ACTION_CHAT,
                "intent": intent
            }
            
        except Exception as e:
            logger.error(f"Error in chat response: {str(e)}", exc_info=True)
            return {
                "response": "Welcome to Jhimki! 🙏 We specialize in handcrafted sarees, suit sets, and fabrics. What can I help you find today?",
                "products": [],
                "action": self.ACTION_CHAT,
                "intent": intent
            }
    
    def _format_products(self, matches: List[Any]) -> List[Dict[str, Any]]:
        """
        Format Pinecone matches into product objects for frontend.
        """
        products = []
        for match in matches:
            # Get price and format it
            price_value = match.metadata.get('price', 'N/A')
            if price_value != 'N/A' and price_value:
                try:
                    price_formatted = f"₹{float(price_value):,.0f}"
                except (ValueError, TypeError):
                    price_formatted = str(price_value)
            else:
                price_formatted = 'N/A'
            
            product = {
                'id': match.id,
                'product_id': match.metadata.get('product_id', match.id),
                'name': match.metadata.get('product_name', 'Unknown'),
                'price': price_formatted,
                'category': match.metadata.get('category', ''),
                'subcategory': match.metadata.get('subcategory', ''),
                'color': match.metadata.get('color', ''),
                'fabric': match.metadata.get('fabric', ''),
                'technique': match.metadata.get('technique', ''),
                'pattern': match.metadata.get('pattern', ''),
                'description': match.metadata.get('description', ''),
                'in_stock': match.metadata.get('in_stock', True),
                'colors_available': match.metadata.get('colors_available', ''),
                'score': round(match.score, 4)
            }
            products.append(product)
        
        return products
    
    def _generate_search_response(self, intent: Dict[str, Any], 
                                 products: List[Dict[str, Any]], 
                                 session: ConversationSession) -> str:
        """
        Generate a natural language response for search results using retrieved product data from Pinecone.
        This uses GPT to format the response according to Jhimki Stock Assistant guidelines.
        """
        # Prepare product information for GPT
        product_summaries = []
        for i, product in enumerate(products[:5]):  # Limit to top 5 for response generation
            in_stock_status = "In Stock" if product.get('in_stock', True) else "Out of Stock"
            summary = f"""
Product {i+1}:
- Name: {product.get('name', 'Unknown')}
- Category: {product.get('category', '')} / {product.get('subcategory', '')}
- Fabric: {product.get('fabric', '')}
- Technique: {product.get('technique', '')}
- Color: {product.get('color', '')}
- Pattern: {product.get('pattern', '')}
- Price: {product.get('price', 'N/A')}
- Stock: {in_stock_status}
- Description: {product.get('description', '')}
"""
            product_summaries.append(summary)
        
        # Build the query context
        attributes = intent.get("attributes", {})
        search_terms = []
        if attributes.get("color"):
            search_terms.append(f"color: {attributes['color']}")
        if attributes.get("fabric"):
            search_terms.append(f"fabric: {attributes['fabric']}")
        if attributes.get("technique"):
            search_terms.append(f"technique: {attributes['technique']}")
        if attributes.get("price_max"):
            search_terms.append(f"under ₹{attributes['price_max']}")
        
        query_description = ", ".join(search_terms) if search_terms else intent.get("search_query", "your request")
        
        system_prompt = """You are the Jhimki Stock Assistant. Format search results warmly and professionally.

RESPONSE FORMAT RULES:
1. First line: Clear answer about match status
   - If good matches: "Yes, we have X options that match your request." or similar
   - If no strong matches: "We don't have exactly that, but here are the closest options I can suggest."
   - If NO matches at all: "I don't see any products matching [criteria] in our current collection."

2. Then list 2-4 best products (max 5) in this format for EACH:
   • [Product Name]
     Category / Fabric / Technique / Color
     Price | Stock Status
     One-line description

3. STRICT RULES:
   - Use ONLY the product data provided
   - DO NOT invent or modify prices, names, fabrics, or stock status
   - Prefer in-stock items unless user asks for out-of-stock
   - Keep descriptions concise (one line each)
   - Warm, customer-friendly tone for an Indian handcrafted fashion brand

Example format:
"Yes, we have 3 beautiful indigo ajrakh cotton sarees that match your request:

• Indigo Ajrakh Cotton Saree with Blouse
  Saree / Cotton / Ajrakh Natural Dye / Indigo
  ₹2,850 | In Stock
  Handwoven cotton with traditional ajrakh block printing

• Indigo Geometric Ajrakh Saree
  Saree / Khadi Cotton / Ajrakh Block Print / Indigo
  ₹2,950 | In Stock
  Elegant geometric patterns with natural dyes

Would you like more details on any of these?"
"""
        
        if not products:
            # No products found - generate helpful response
            user_prompt = f"""User searched for: {query_description}
No matching products were found in our database.

Generate a polite response explaining we don't have that exact item, and suggest they:
1. Try different color/fabric options
2. Browse similar categories
Keep it brief and helpful."""
        else:
            # Products found - format them
            products_text = "\n".join(product_summaries)
            user_prompt = f"""User searched for: {query_description}
Found {len(products)} products from our Pinecone database.

RETRIEVED PRODUCTS FROM DATABASE:
{products_text}

Generate a warm response following the format rules. List 2-4 best matches (prioritize in-stock items).
Use ONLY the exact data provided above. Do not invent details."""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating search response: {str(e)}", exc_info=True)
            # Fallback response
            if not products:
                return f"I couldn't find any products matching {query_description}. Would you like to try a different color or style?"
            else:
                count = len(products)
                return f"I found {count} items matching your search. Here are the results!"
    
    def clear_session(self, session_id: str):
        """Clear a conversation session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared session: {session_id}")
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            return {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "last_updated": session.last_updated.isoformat(),
                "message_count": len(session.messages),
                "context": session.context
            }
        return None
