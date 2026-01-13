"""
Admin Routes - System administration and statistics
"""
from fastapi import APIRouter, Depends

from src.database import get_all_users, get_system_stats
from src.llm import get_available_models
from ..dependencies import require_admin

router = APIRouter()

@router.get("/users")
def admin_get_users(user: dict = Depends(require_admin)):
    """Admin: Get all users"""
    return {"users": get_all_users()}

@router.get("/stats")
def admin_get_stats(user: dict = Depends(require_admin)):
    """Admin: Get system statistics"""
    return get_system_stats()

@router.get("/models")
def list_available_models():
    """Get list of available LLM models (public endpoint)"""
    return {"models": get_available_models()}