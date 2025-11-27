from pinecone_search import PineconeSearchService

# Initialize service with hardcoded credentials
api_key = "pcsk_6nuahb_98J8VPsATTv1hPsGz8MPcQ94ZbZjhkfruM95ah92qJgaCqnE5BTZaNjit1uCgfP"
index_name = "tranquil-eucalyptus"
search_service = PineconeSearchService(api_key=api_key, index_name=index_name)

# Search with a string
search_query = "red silk saree"
results = search_service.search(query_text=search_query, top_k=5)

# Print output
print(f"Found {len(results)} results for: '{search_query}'\n")

for i, match in enumerate(results, 1):
    print(f"{i}. {match.metadata.get('product_name', 'Unknown')}")
    print(f"   Score: {match.score:.4f}")
    print(f"   Price: ₹{match.metadata.get('price', 'N/A')}\n")
