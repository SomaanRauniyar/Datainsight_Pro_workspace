import os
from pinecone import Pinecone, ServerlessSpec
from concurrent.futures import ThreadPoolExecutor

# Default Pinecone config from env
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "biz-analyst")


def get_pinecone_config(user_id: str = None):
    """Get Pinecone API key and index - uses user's keys if available"""
    api_key = PINECONE_API_KEY
    index_name = PINECONE_INDEX
    
    if user_id:
        try:
            from src.user_keys import get_effective_key
            user_key = get_effective_key(user_id, "pinecone_api_key")
            user_index = get_effective_key(user_id, "pinecone_index")
            
            if user_key:
                api_key = user_key
            if user_index:
                index_name = user_index
        except Exception as e:
            print(f"[VectorManager] Error getting user keys: {e}")
    
    return api_key, index_name


class VectorDBManager:
    def __init__(self, api_key=None, index_name=None, dimension=1024, metric="cosine", user_id=None):
        """
        Pinecone ke saath vector database manager banata hai.
        Index ko create karega agar exist nahi karta ho.
        
        If user_id is provided, will use user's Pinecone keys if available.
        """
        # Get config - user keys take priority
        if user_id and (api_key is None or index_name is None):
            user_api_key, user_index = get_pinecone_config(user_id)
            api_key = api_key or user_api_key
            index_name = index_name or user_index
        
        # Fall back to env vars
        api_key = api_key or PINECONE_API_KEY
        index_name = index_name or PINECONE_INDEX
        
        if not api_key:
            raise ValueError("No Pinecone API key available")
        
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name

        # Sab indexes ka list nikaalo
        existing_indexes = [i.name for i in self.pc.list_indexes()]

        target_index = self.index_name
        needs_create = False

        if target_index in existing_indexes:
            print(f"✅ Index '{target_index}' already exists!")
            # Try to detect dimension mismatch and transparently switch to a dimension-suffixed index
            try:
                desc = self.pc.describe_index(target_index)
                existing_dim = getattr(desc, "dimension", None) or getattr(desc, "config", {}).get("dimension")
                if existing_dim and int(existing_dim) != int(dimension):
                    suggested = f"{target_index}-{dimension}"
                    print(
                        f"⚠️ Index dimension mismatch: existing={existing_dim}, required={dimension}. "
                        f"Will use '{suggested}' instead."
                    )
                    target_index = suggested
                    if target_index not in existing_indexes:
                        needs_create = True
                # else: ok to use existing index
            except Exception:
                # If describe fails, fall back to using requested name; will create if needed
                pass
        else:
            needs_create = True

        if needs_create:
            print(f"📌 Creating Pinecone index: {target_index}")
            self.pc.create_index(
                name=target_index,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )

        # Ensure we use the final resolved index name
        self.index_name = target_index

        # Index attach karo
        self.index = self.pc.Index(self.index_name)

    def upsert_vectors(self, vectors, namespace="default", batch_size=20, max_workers=4):
        """
        Upload embeddings to Pinecone in parallel batches to improve speed.
        Args:
            vectors: list of dicts [{id, values, metadata}]
            namespace: Pinecone namespace string
            batch_size: number of vectors per batch
            max_workers: number of parallel upsert threads
        """
        n = len(vectors)
        batches = [vectors[i:i + batch_size] for i in range(0, n, batch_size)]

        def upsert_batch(batch):
            self.index.upsert(vectors=batch, namespace=namespace)
            print(f"✅ Batch upserted {len(batch)} vectors into '{self.index_name}' [namespace={namespace}]")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(upsert_batch, batches)

    def query(self, vector, top_k=5, namespace="default"):
        """
        Similarity search given vector against Pinecone index.
        """
        result = self.index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            namespace=namespace
        )
        return result


# 🧪 For local testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX = os.getenv("PINECONE_INDEX", "biz-analyst")

    db = VectorDBManager(api_key=PINECONE_API_KEY, index_name=PINECONE_INDEX)

    sample_vectors = [
        {"id": "vec1", "values": [0.1] * 384, "metadata": {"content": "Hello world!"}}
    ]

    db.upsert_vectors(sample_vectors)

    q = db.query([0.1] * 384, top_k=2)
    print(q)