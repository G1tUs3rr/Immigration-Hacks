import logging
import os
import openai
import pinecone
from pinecone import Pinecone, ServerlessSpec
from app.config import (
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    PINECONE_INDEX_NAME,
    EMBEDDING_MODEL_NAME, # This will now be 'text-embedding-3-small'
    EMBEDDING_DIMENSION,  # This will be 1536 for text-embedding-3-small
    OPENAI_API_KEY        # Added for OpenAI
)

logger = logging.getLogger(__name__)

# --- OpenAI Client Initialization ---
# The OpenAI client is typically initialized when needed, or once globally.
# For simplicity here, we'll ensure the API key is set.
if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_PLACEHOLDER":
    logger.warning("OPENAI_API_KEY not set or is placeholder. OpenAI embeddings will fail.")
    # openai.api_key will not be set, calls will fail.
else:
    openai.api_key = OPENAI_API_KEY
    logger.info("OpenAI API key configured.")


async def generate_embedding(text: str, model: str = EMBEDDING_MODEL_NAME): # model parameter defaults to config
    """
    Generates an embedding for the given text using the specified OpenAI model.
    """
    if not openai.api_key:
        logger.error("OpenAI API key not configured. Cannot generate embedding.")
        return None
    if not isinstance(text, (str, list)):
        logger.error(f"Invalid input type for embedding: {type(text)}. Expected str or list of str.")
        return None
    
    # OpenAI API expects a list of strings for batching, or a single string.
    # If a single string, it's better to wrap it in a list for consistency with the API's batch processing.
    input_texts = [text] if isinstance(text, str) else text
    
    # Replace newlines for OpenAI's recommendation
    input_texts = [item.replace("\n", " ") for item in input_texts]

    try:
        # Create async client
        client = openai.AsyncOpenAI(api_key=openai.api_key)
        
        # Use async client to create embeddings
        response = await client.embeddings.create(input=input_texts, model=model)
        
        # The response object has a 'data' attribute that contains a list of embedding objects
        # Each embedding object has an 'embedding' attribute
        embeddings = [item.embedding for item in response.data]
        
        if isinstance(text, str): # If original input was a single string, return a single embedding
            return embeddings[0]
        else: # If original input was a list, return a list of embeddings
            return embeddings
            
    except openai.APIError as e: # More specific error handling for OpenAI
        logger.error(f"OpenAI API error generating embedding: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error generating OpenAI embedding for text: '{str(text)[:100]}...': {e}", exc_info=True)
        return None

# --- Pinecone Initialization ---
pc = None
index = None

def init_pinecone():
    global pc, index
    if not all([PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME]):
        if PINECONE_API_KEY == "YOUR_PINECONE_API_KEY_PLACEHOLDER" or \
        PINECONE_ENVIRONMENT == "YOUR_PINECONE_ENVIRONMENT_PLACEHOLDER":
            logger.warning("Pinecone API Key or Environment is using placeholder values. Pinecone will not be initialized.")
            return False
        logger.error("Pinecone configuration (API_KEY, ENVIRONMENT, INDEX_NAME) incomplete in config.py.")
        return False

    try:
        pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
        
        # Check if index exists
        if PINECONE_INDEX_NAME not in pinecone.list_indexes():
            logger.info(f"Pinecone index '{PINECONE_INDEX_NAME}' does not exist. Attempting to create it.")
            try:
                pinecone.create_index(
                    name=PINECONE_INDEX_NAME,
                    dimension=EMBEDDING_DIMENSION,
                    metric="cosine"
                )
                logger.info(f"Pinecone index '{PINECONE_INDEX_NAME}' created successfully with dimension {EMBEDDING_DIMENSION}.")
            except Exception as create_e:
                logger.error(f"Failed to create Pinecone index '{PINECONE_INDEX_NAME}': {create_e}", exc_info=True)
                return False
        
        index = pinecone.Index(PINECONE_INDEX_NAME)
        logger.info(f"Successfully connected to Pinecone index: {PINECONE_INDEX_NAME}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {e}", exc_info=True)
        return False

# Attempt to initialize Pinecone when the module is loaded.
# For FastAPI, this could also be triggered by a startup event in main.py
if not init_pinecone():
    logger.warning("Pinecone not initialized. Vector store operations will be degraded or fail.")


async def upsert_vectors(vectors: list, batch_size: int = 100):
    """
    Upserts vectors into the Pinecone index.
    Expects vectors in the format: [(id1, embedding1, metadata1), (id2, embedding2, metadata2), ...]
    """
    if not index:
        logger.error("Pinecone index is not initialized. Cannot upsert vectors.")
        return None
    if not vectors:
        logger.warning("No vectors provided to upsert.")
        return None

    def process_vector_id(vector_id: str) -> str:
        """Process vector ID to ensure it meets Pinecone's requirements."""
        # First, clean the ID by replacing newlines and multiple spaces with single spaces
        cleaned_id = ' '.join(vector_id.replace('\n', ' ').split())
        
        # If the cleaned ID is already short enough, return it
        if len(cleaned_id) <= 512:
            return cleaned_id
        
        # If still too long, create a hash of the entire ID
        import hashlib
        hash_suffix = hashlib.md5(cleaned_id.encode()).hexdigest()[:8]
        
        # Take first 503 characters of cleaned ID and add hash
        truncated_id = cleaned_id[:503] + "_" + hash_suffix  # 503 + 1 + 8 = 512
        
        logger.warning(f"Vector ID was too long ({len(cleaned_id)} chars). Truncated to '{truncated_id}'")
        return truncated_id

    try:
        upsert_responses = []
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            # Process each vector in the batch to ensure IDs meet requirements
            processed_batch = [
                (process_vector_id(str(id_)), embedding, metadata)
                for id_, embedding, metadata in batch
            ]
            
            logger.debug(f"Upserting batch of {len(processed_batch)} vectors to Pinecone.")
            response = index.upsert(vectors=processed_batch)
            upsert_responses.append(response)
            logger.info(f"Successfully upserted batch to Pinecone. Upserted count: {response.upserted_count}")
        return upsert_responses
    except Exception as e:
        logger.error(f"Error upserting vectors to Pinecone: {e}", exc_info=True)
        return None


async def query_vector_store(query_text: str, top_k: int = 20, filter_criteria: dict = None):
    """
    Queries the Pinecone vector store for relevant documents using cosine similarity (if index is configured for it).
    Returns top_k embeddings along with their metadata.
    """
    if not index:
        logger.error("Pinecone index is not initialized. Cannot query.")
        # Fallback to simulated response if Pinecone is not available
        logger.info(f"Simulating querying vector store for: '{query_text}' with top_k={top_k}. (Pinecone not initialized)")
        return [
            {"id": "sim_doc1", "score": 0.9, "metadata": {"text": "This is a simulated relevant document because Pinecone is not available."}},
            {"id": "sim_doc2", "score": 0.85, "metadata": {"text": "Another simulated document discussing laws, due to Pinecone unavailability."}}
        ]
    if not openai.api_key: # Check if OpenAI client is ready
        logger.error("OpenAI API key not configured. Cannot generate query embedding.")
        return []

    try:
        query_embedding = await generate_embedding(query_text)
        if not query_embedding:
            logger.error("Failed to generate embedding for the query.")
            return []

        query_params = {
            "vector": query_embedding,
            "top_k": top_k,
            "include_metadata": True
        }
        if filter_criteria:
            query_params["filter"] = filter_criteria
        
        logger.debug(f"Querying Pinecone with top_k={top_k}, filter={filter_criteria}")
        query_response = index.query(**query_params)
        
        matches = query_response.get('matches', [])
        logger.info(f"Query to Pinecone for '{query_text[:50]}...' returned {len(matches)} matches.")
        
        # Example processing:
        # results = [{"id": match.id, "score": match.score, "text": match.metadata.get("text")} for match in matches]
        return matches

    except Exception as e:
        logger.error(f"Error querying Pinecone: {e}", exc_info=True)
        return []


async def delete_vectors(ids: list = None, delete_all: bool = False, namespace: str = None):
    """
    Deletes vectors from the Pinecone index by IDs or deletes all vectors in a namespace.
    """
    if not index:
        logger.error("Pinecone index is not initialized. Cannot delete vectors.")
        return False
    try:
        if delete_all:
            logger.info(f"Attempting to delete all vectors in namespace: {namespace if namespace else 'default'}")
            response = index.delete(delete_all=True, namespace=namespace)
        elif ids:
            logger.info(f"Attempting to delete {len(ids)} vectors by ID.")
            response = index.delete(ids=ids, namespace=namespace)
        else:
            logger.warning("No IDs provided and delete_all is False. Nothing to delete.")
            return False
        
        logger.info(f"Pinecone delete response: {response}") # Pinecone delete returns an empty dict {} on success
        return True # Assuming success if no exception
    except Exception as e:
        logger.error(f"Error deleting vectors from Pinecone: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    import asyncio

    # This basic test assumes you have .env file with REAL credentials
    # and the index either exists or can be created.
    # For a more robust test, you might mock Pinecone and SentenceTransformer.
    async def main_test():
        logger.info("Starting vector_store.py direct test...")
        # init_pinecone() is called at module load, but we can check its status
        if not index or not embedding_model:
            logger.error("Pinecone index or embedding model not initialized. Aborting test.")
            print("Pinecone index or embedding model not initialized. Check logs and .env file. Aborting test.")
            return

        print(f"Testing with Pinecone index: {PINECONE_INDEX_NAME}")
        print(f"Testing with Embedding model: {EMBEDDING_MODEL_NAME} (Dimension: {EMBEDDING_DIMENSION})")

        # Test embedding generation
        test_sentence = "What are the requirements for a U visa?"
        embedding = await generate_embedding(test_sentence)
        if embedding:
            print(f"\nSuccessfully generated embedding for: '{test_sentence}'")
            print(f"Embedding dimension: {len(embedding)}")
        else:
            print(f"\nFailed to generate embedding for: '{test_sentence}'")
            return # Cannot proceed without embeddings

        # Test Upsert
        print("\nTesting upsert...")
        doc1_embedding = await generate_embedding("This is a test document about immigration policies.")
        doc2_embedding = await generate_embedding("Another test document focusing on visa applications.")
        sample_vectors_to_upsert = []
        if doc1_embedding:
            sample_vectors_to_upsert.append(("test_doc_1", doc1_embedding, {"source": "test_data", "topic": "policy"}))
        if doc2_embedding:
            sample_vectors_to_upsert.append(("test_doc_2", doc2_embedding, {"source": "test_data", "topic": "visa"}))

        if sample_vectors_to_upsert:
            upsert_result = await upsert_vectors(sample_vectors_to_upsert)
            if upsert_result:
                print(f"Upsert successful (details in logs).") # Response is a list of Pinecone responses
            else:
                print("Upsert failed (details in logs).")
        else:
            print("Failed to generate embeddings for sample documents. Skipping upsert test.")


        # Test Query
        print("\nTesting query...")
        query = "Tell me about visa applications"
        results = await query_vector_store(query, top_k=2)
        if results:
            print(f"Query: '{query}'")
            for i, res_match in enumerate(results): # Pinecone client returns Match objects in v3+
                print(f"  Result {i+1}: ID: {res_match.id}, Score: {res_match.score:.4f}, Metadata: {res_match.metadata}")
        else:
            print(f"No results or error for query: '{query}' (details in logs).")

        # Test Query with Filter
        print("\nTesting query with filter (topic: policy)...")
        results_filtered = await query_vector_store(query, top_k=1, filter_criteria={"topic": "policy"})
        if results_filtered:
            print(f"Query: '{query}', Filter: {{'topic': 'policy'}}")
            for i, res_match in enumerate(results_filtered):
                print(f"  Result {i+1}: ID: {res_match.id}, Score: {res_match.score:.4f}, Metadata: {res_match.metadata}")
        else:
            print(f"No results or error for filtered query (details in logs).")

        # Test Delete (cleanup)
        # print("\nTesting delete...")
        # ids_to_delete = ["test_doc_1", "test_doc_2"]
        # delete_success = await delete_vectors(ids=ids_to_delete)
        # if delete_success:
        #     print(f"Successfully initiated delete for IDs: {ids_to_delete} (check logs for confirmation from Pinecone).")
        #     # Verify deletion by trying to fetch them ( Pinecone fetch is by ID list )
        #     # fetched = index.fetch(ids=ids_to_delete)
        #     # if not fetched.vectors:
        #     #     print("Deletion verified: Vectors no longer found.")
        #     # else:
        #     #     print(f"Deletion verification failed: Vectors still found: {fetched.vectors.keys()}")
        # else:
        #     print(f"Delete operation failed for IDs: {ids_to_delete} (details in logs).")
        
        # print("\nTo fully test delete_all, uncomment the following and ensure your .env points to a TEST index:")
        # print("Be careful with delete_all=True on a production index!")
        # delete_all_success = await delete_vectors(delete_all=True)
        # if delete_all_success:
        #     print("Successfully initiated delete_all operation.")
        # else:
        #     print("delete_all operation failed.")

    if os.getenv("PINECONE_API_KEY") != "YOUR_PINECONE_API_KEY_PLACEHOLDER" and \
    os.getenv("PINECONE_ENVIRONMENT") != "YOUR_PINECONE_ENVIRONMENT_PLACEHOLDER":
        asyncio.run(main_test())
    else:
        print("Skipping vector_store.py direct test because Pinecone credentials are placeholders in .env or environment.")
        print("Please set actual PINECONE_API_KEY and PINECONE_ENVIRONMENT to run the test.")
    # print("vector_store.py can be tested when config.py is set up with Pinecone credentials and an embedding mechanism.")