"""
Query Routes - RAG queries and data schema endpoints
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional

from src.query_llm import query_llm
from src.database import log_token_usage
from ..dependencies import get_current_user, get_data_cache

router = APIRouter()
legacy_router = APIRouter()  # For backward compatibility

@router.post("/")
def query_text(
    user_query: str = Query(...),
    user_id: str = Query(...),
    file_id: str = Query(...),
    model: Optional[str] = Query("auto"),
    user: dict = Depends(get_current_user)
):
    """Query uploaded documents using RAG"""
    effective_user_id = str(user["user_id"]) if user else user_id
    namespace = f"user_{effective_user_id}_{file_id}"
    
    try:
        result = query_llm(user_query, namespace=namespace, user_id=effective_user_id, model=model)
        
        # Log token usage
        if user:
            try:
                log_token_usage(user["user_id"], 500, "query")  # Estimate
            except:
                pass  # Don't fail if logging fails
        
        return result
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[ERROR] Query failed: {str(e)}")
        print(f"[ERROR] Traceback: {error_details}")
        
        # Return user-friendly error
        error_msg = str(e)
        if "namespace" in error_msg.lower() or "no matches" in error_msg.lower():
            raise HTTPException(
                status_code=400, 
                detail="No data found for this file. Please make sure the file was uploaded successfully and processing completed."
            )
        elif "pinecone" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail="Vector database connection error. Please try again in a moment."
            )
        else:
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@router.get("/schema")
def get_schema(
    user_id: str = Query(...), 
    file_id: str = Query(...),
    data_cache: dict = Depends(get_data_cache)
):
    """Get data schema for uploaded file"""
    df = data_cache.get((user_id, file_id))
    if df is None or df.empty:
        return {"columns": [], "types": {}}
    
    import pandas as pd
    types = {}
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            t = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(df[c]):
            t = "datetime"
        else:
            t = "categorical"
        types[c] = t
    
    return {"columns": list(df.columns), "types": types}

# Legacy endpoints for backward compatibility
@legacy_router.post("/query")
def query_text_legacy(
    user_query: str = Query(...),
    user_id: str = Query(...),
    file_id: str = Query(...),
    model: Optional[str] = Query("auto"),
    user: dict = Depends(get_current_user)
):
    """Legacy query endpoint"""
    return query_text(user_query, user_id, file_id, model, user)

@legacy_router.get("/schema")
def get_schema_legacy(
    user_id: str = Query(...), 
    file_id: str = Query(...),
    data_cache: dict = Depends(get_data_cache)
):
    """Legacy schema endpoint"""
    return get_schema(user_id, file_id, data_cache)