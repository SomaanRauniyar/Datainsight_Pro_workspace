import os
import json
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple, Optional

from src.vector_manager import VectorDBManager
from src.embeddings import get_embedding
from src.llm import ask_llm

load_dotenv()

MAX_CONTEXT_CHARS = 3000
TOP_K = 6

def _format_sources(matches: List[Dict[str, Any]], max_chars: int) -> Tuple[str, List[Dict[str, Any]]]:
    parts = []
    sources = []
    total_len = 0

    for i, m in enumerate(matches):
        meta = m.get("metadata", {})
        content = meta.get("content", "") or meta.get("text", "")
        snippet = content.strip().replace("\n", " ")
        if len(snippet) > 400:
            snippet = snippet[:397] + "..."
        src_id = meta.get("chunk_id") or m.get("id") or f"match-{i}"
        file_id = meta.get("file_id", meta.get("source", "unknown"))
        score = m.get("score") or m.get("similarity") or None

        entry_text = f"[{i+1}] id:{src_id} file:{file_id} score:{score}\n{snippet}\n"
        entry_len = len(entry_text)

        if total_len + entry_len > max_chars:
            break

        parts.append(entry_text)
        total_len += entry_len

        sources.append({
            "index": i+1,
            "chunk_id": src_id,
            "file_id": file_id,
            "score": score,
            "snippet": snippet,
            "raw": content
        })

    context_text = "\n".join(parts)
    return context_text, sources


def _build_prompt(user_query: str, context_text: str) -> str:
    prompt = f"""
System: You are a careful business analyst assistant. You MUST answer using ONLY the facts present in the provided CONTEXT. 
If the answer is not contained in the context, answer exactly: "I don't know — the documents don't contain that information."

User Query:
{user_query}

CONTEXT (use only this):
{context_text}

RESPONSE FORMAT (JSON only):
Return a JSON object with keys:
- answer: a concise, well-structured answer to the user's query (string).
- sources: a list of objects with keys [index, chunk_id, file_id, score] referencing the context entries used.
- notes: optional short explanation if you had to say "I don't know".

Important: Do not add any extra text outside the JSON. Do not include chain-of-thought.
"""
    return prompt


def query_llm(query: str, top_k: int = TOP_K, max_context_chars: int = MAX_CONTEXT_CHARS, namespace: str = None, user_id: str = None, model: str = "auto") -> Dict[str, Any]:
    """
    Query the RAG system with optional user_id for using user's own API keys.
    Uses user's model preference if set, or the provided model parameter.
    """
    # Use provided model, or get user's preference
    model_to_use = model
    if model == "auto" and user_id:
        try:
            from src.user_keys import get_user_preference
            saved_model = get_user_preference(user_id, "model", "auto")
            if saved_model and saved_model != "llama-3.1-70b-versatile":  # Skip deprecated
                model_to_use = saved_model
        except:
            pass
    
    # Get Pinecone config (uses user keys if available)
    pinecone_api_key, pinecone_index = None, None
    if user_id:
        try:
            from src.user_keys import get_effective_key
            pinecone_api_key = get_effective_key(user_id, "pinecone_api_key")
            pinecone_index = get_effective_key(user_id, "pinecone_index")
        except:
            pass
    
    # Fall back to env vars
    pinecone_api_key = pinecone_api_key or os.getenv("PINECONE_API_KEY")
    pinecone_index = pinecone_index or os.getenv("PINECONE_INDEX", "biz-analyst")
    
    db = VectorDBManager(api_key=pinecone_api_key, index_name=pinecone_index)
    query_vector = get_embedding(query, is_query=True, user_id=user_id)

    if namespace:
        result = db.query(vector=query_vector, top_k=top_k, namespace=namespace)
    else:
        result = db.query(vector=query_vector, top_k=top_k)

    matches = result.get("matches", []) if isinstance(result, dict) else result.matches

    context_text, sources = _format_sources(matches, max_context_chars)

    if not context_text.strip():
        return {
            "answer": "I don't know — there were no relevant documents found.",
            "sources": []
        }

    prompt = _build_prompt(query, context_text)
    llm_response = ask_llm(prompt, model=model_to_use, user_id=user_id)

    try:
        parsed = json.loads(llm_response.strip())
        parsed["resolved_sources"] = sources
        parsed["model_used"] = model_to_use
        return parsed
    except Exception:
        return {
            "answer": llm_response.strip(),
            "sources": sources,
            "model_used": model_to_use,
            "warning": "LLM response was not valid JSON."
        }

if __name__ == "__main__":
    test_query = "Summarize the key business insights from uploaded documents."
    out = query_llm(test_query)
    print("ANSWER:\n", out.get("answer"))
    print("\nSOURCES:")
    for s in out.get("resolved_sources", out.get("sources", [])):
        print(s)