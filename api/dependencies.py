"""
API Dependencies - Shared dependencies for route handlers
"""
from fastapi import Header, HTTPException, Request
from typing import Optional

from src.auth import AuthService

async def get_current_user(authorization: Optional[str] = Header(None)):
    """Validate auth token and return user info (optional)"""
    if not authorization:
        return None
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    user = AuthService.validate_token(token)
    return user

async def require_auth(authorization: Optional[str] = Header(None)):
    """Require authentication - raises 401 if not authenticated"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

async def require_admin(user: dict = require_auth):
    """Require admin privileges"""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def get_vector_db(request: Request):
    """Get vector database instance from app state"""
    return request.app.state.vector_db

def get_data_cache(request: Request):
    """Get data cache from app state"""
    return request.app.state.data_cache

def get_upload_jobs(request: Request):
    """Get upload jobs tracker from app state"""
    return request.app.state.upload_jobs