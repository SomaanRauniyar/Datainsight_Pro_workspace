import os
from dotenv import load_dotenv
import cohere

# Load env once
load_dotenv()

# Cohere configuration
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
COHERE_EMBED_MODEL = os.getenv("COHERE_EMBED_MODEL", "embed-english-v3.0")
# Use "search_document" for corpus/doc vectors; use "search_query" when embedding queries
COHERE_INPUT_TYPE_DOCUMENT = os.getenv("COHERE_INPUT_TYPE_DOCUMENT", "search_document")
COHERE_INPUT_TYPE_QUERY = os.getenv("COHERE_INPUT_TYPE_QUERY", "search_query")

# Initialize default Cohere client
_default_client = None

def get_default_client():
    global _default_client
    if _default_client is None and COHERE_API_KEY:
        _default_client = cohere.Client(COHERE_API_KEY)
    return _default_client


def get_client_for_user(user_id: str = None):
    """Get Cohere client - uses user's key if available, otherwise system key"""
    if user_id:
        try:
            from src.user_keys import get_effective_key
            user_key = get_effective_key(user_id, "cohere_api_key")
            if user_key and user_key != COHERE_API_KEY:
                return cohere.Client(user_key)
        except Exception as e:
            print(f"[Embeddings] Error getting user key: {e}")
    
    return get_default_client()


def get_embedding(text: str, *, is_query: bool = False, user_id: str = None):
    """
    Return embedding vector for a given text using Cohere embeddings API.
    Set is_query=True when embedding user queries to improve retrieval quality.
    """
    client = get_client_for_user(user_id)
    if client is None:
        raise ValueError("No Cohere API key available")
    
    input_type = COHERE_INPUT_TYPE_QUERY if is_query else COHERE_INPUT_TYPE_DOCUMENT
    resp = client.embed(
        texts=[text],
        model=COHERE_EMBED_MODEL,
        input_type=input_type,
    )
    return resp.embeddings[0]


def embed_chunks(chunks, user_id: str = None):
    """
    Add embedding for each chunk in batch using Cohere embeddings API.
    Expects each chunk to contain key "content".
    Handles large batches by splitting into smaller requests.
    """
    if not chunks:
        return chunks

    client = get_client_for_user(user_id)
    if client is None:
        raise ValueError("No Cohere API key available")

    # Cohere has a limit of 96 texts per request
    BATCH_SIZE = 96
    
    texts = [chunk.get("content", "")[:8000] for chunk in chunks]  # Truncate long texts
    all_vectors = []
    
    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i:i + BATCH_SIZE]
        try:
            resp = client.embed(
                texts=batch_texts,
                model=COHERE_EMBED_MODEL,
                input_type=COHERE_INPUT_TYPE_DOCUMENT,
            )
            all_vectors.extend(resp.embeddings)
        except Exception as e:
            print(f"[Embeddings] Error embedding batch {i//BATCH_SIZE}: {e}")
            # Create zero vectors for failed batch
            from src.config import EMBED_DIM
            all_vectors.extend([[0.0] * EMBED_DIM for _ in batch_texts])

    for i, chunk in enumerate(chunks):
        if i < len(all_vectors):
            chunk["embedding"] = all_vectors[i]
        else:
            from src.config import EMBED_DIM
            chunk["embedding"] = [0.0] * EMBED_DIM

    return chunks