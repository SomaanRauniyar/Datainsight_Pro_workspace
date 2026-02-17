import os
from dotenv import load_dotenv
import cohere
import requests

# Load env once
load_dotenv()

# Voyage AI configuration (primary)
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "voyage-3")
VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"

# Cohere configuration (fallback)
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
COHERE_EMBED_MODEL = os.getenv("COHERE_EMBED_MODEL", "embed-english-v3.0")
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


def get_voyage_embedding(text: str, is_query: bool = False):
    """Get embedding from Voyage AI"""
    if not VOYAGE_API_KEY:
        return None
    
    try:
        input_type = "query" if is_query else "document"
        headers = {
            "Authorization": f"Bearer {VOYAGE_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "input": [text],
            "model": VOYAGE_MODEL,
            "input_type": input_type
        }
        
        response = requests.post(VOYAGE_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["data"][0]["embedding"]
    except Exception as e:
        print(f"[Embeddings] Voyage AI error: {e}")
        return None


def get_embedding(text: str, *, is_query: bool = False, user_id: str = None):
    """
    Return embedding vector for a given text.
    Tries Voyage AI first, falls back to Cohere if needed.
    Set is_query=True when embedding user queries to improve retrieval quality.
    """
    # Try Voyage AI first (works on cloud servers)
    voyage_embedding = get_voyage_embedding(text, is_query=is_query)
    if voyage_embedding is not None:
        print(f"[Embeddings] Using Voyage AI")
        return voyage_embedding
    
    # Fallback to Cohere
    print(f"[Embeddings] Falling back to Cohere")
    client = get_client_for_user(user_id)
    if client is None:
        raise ValueError("No embedding API key available (tried Voyage AI and Cohere)")
    
    input_type = COHERE_INPUT_TYPE_QUERY if is_query else COHERE_INPUT_TYPE_DOCUMENT
    resp = client.embed(
        texts=[text],
        model=COHERE_EMBED_MODEL,
        input_type=input_type,
    )
    return resp.embeddings[0]


def embed_chunks(chunks, user_id: str = None):
    """
    Add embedding for each chunk in batch.
    Uses Voyage AI for better cloud server compatibility.
    Expects each chunk to contain key "content".
    """
    if not chunks:
        return chunks

    # Try Voyage AI batch embedding first
    if VOYAGE_API_KEY:
        try:
            texts = [chunk.get("content", "")[:8000] for chunk in chunks]
            headers = {
                "Authorization": f"Bearer {VOYAGE_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "input": texts,
                "model": VOYAGE_MODEL,
                "input_type": "document"
            }
            
            response = requests.post(VOYAGE_API_URL, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            for i, chunk in enumerate(chunks):
                if i < len(result["data"]):
                    chunk["embedding"] = result["data"][i]["embedding"]
            
            print(f"[Embeddings] Batch embedded {len(chunks)} chunks with Voyage AI")
            return chunks
        except Exception as e:
            print(f"[Embeddings] Voyage AI batch error: {e}, falling back to Cohere")

    # Fallback to Cohere
    client = get_client_for_user(user_id)
    if client is None:
        raise ValueError("No embedding API key available")

    # Cohere has a limit of 96 texts per request
    BATCH_SIZE = 96
    
    texts = [chunk.get("content", "")[:8000] for chunk in chunks]
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
            from src.config import EMBED_DIM
            all_vectors.extend([[0.0] * EMBED_DIM for _ in batch_texts])

    for i, chunk in enumerate(chunks):
        if i < len(all_vectors):
            chunk["embedding"] = all_vectors[i]
        else:
            from src.config import EMBED_DIM
            chunk["embedding"] = [0.0] * EMBED_DIM

    return chunks