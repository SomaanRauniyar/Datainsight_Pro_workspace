"""
User Routes - User management, API keys, and preferences
"""
from fastapi import APIRouter, Query, HTTPException, Depends

from src.database import get_user_token_usage, get_user_files
from src.user_keys import (
    save_user_key, get_all_user_keys, delete_user_key, 
    test_api_key, get_effective_key, save_user_preference, 
    get_user_preference, get_all_user_preferences
)
from src.llm import get_available_models
from ..dependencies import require_auth
from ..models import SaveApiKeyRequest, TestApiKeyRequest, ModelPreferenceRequest

router = APIRouter()

@router.get("/files")
def get_user_uploaded_files(user: dict = Depends(require_auth)):
    """Get list of user's uploaded files"""
    files = get_user_files(user["user_id"])
    return {"files": files}

@router.get("/usage")
def get_usage_stats(
    days: int = Query(30),
    user: dict = Depends(require_auth)
):
    """Get user's token usage"""
    tokens = get_user_token_usage(user["user_id"], days)
    return {
        "user_id": user["user_id"],
        "tokens_used": tokens,
        "period_days": days
    }

# ============== API Keys Management ==============

@router.get("/api-keys")
def get_user_api_keys(user: dict = Depends(require_auth)):
    """Get list of which API keys user has saved (not actual values)"""
    keys = get_all_user_keys(user["user_id"])
    return {"keys": keys}

@router.post("/api-keys")
def save_user_api_key(req: SaveApiKeyRequest, user: dict = Depends(require_auth)):
    """Save an API key for the user (encrypted)"""
    valid_keys = ["groq_api_key", "cohere_api_key", "pinecone_api_key", "pinecone_index"]
    
    if req.key_name not in valid_keys:
        raise HTTPException(status_code=400, detail=f"Invalid key name. Must be one of: {valid_keys}")
    
    success = save_user_key(user["user_id"], req.key_name, req.key_value)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save key")
    
    return {"success": True, "message": f"{req.key_name} saved successfully"}

@router.delete("/api-keys/{key_name}")
def delete_user_api_key(key_name: str, user: dict = Depends(require_auth)):
    """Delete a user's API key"""
    success = delete_user_key(user["user_id"], key_name)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete key")
    
    return {"success": True}

@router.post("/api-keys/test")
def test_user_api_key(req: TestApiKeyRequest, user: dict = Depends(require_auth)):
    """Test if a user's saved API key is valid"""
    result = test_api_key(user["user_id"], req.key_name)
    return result

@router.get("/api-keys/debug")
def debug_user_api_keys(user: dict = Depends(require_auth)):
    """Debug: Check what keys are retrieved for user"""
    user_id = user["user_id"]
    
    # Get all saved keys
    saved_keys = get_all_user_keys(user_id)
    
    # Try to get effective keys (masked)
    effective = {}
    for key_name in ["groq_api_key", "cohere_api_key", "pinecone_api_key", "pinecone_index"]:
        val = get_effective_key(user_id, key_name)
        if val:
            if key_name == "pinecone_index":
                effective[key_name] = val  # Show index name fully
            else:
                effective[key_name] = val[:8] + "..." if len(val) > 8 else val
        else:
            effective[key_name] = None
    
    return {
        "user_id": user_id,
        "saved_keys": saved_keys,
        "effective_keys": effective
    }

# ============== Model Preferences ==============

@router.get("/preferences")
def get_preferences(user: dict = Depends(require_auth)):
    """Get user's preferences including model selection"""
    prefs = get_all_user_preferences(user["user_id"])
    return {
        "model": prefs.get("model", "auto"),
        "preferences": prefs
    }

@router.post("/preferences/model")
def set_model_preference(req: ModelPreferenceRequest, user: dict = Depends(require_auth)):
    """Set user's preferred LLM model"""
    available = get_available_models()
    if req.model not in available:
        raise HTTPException(status_code=400, detail=f"Invalid model. Available: {list(available.keys())}")
    
    success = save_user_preference(user["user_id"], "model", req.model)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save preference")
    
    return {"success": True, "model": req.model}