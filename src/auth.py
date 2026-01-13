"""
Authentication module for DataInsight Pro
Supports Clerk (production) or local auth (development)
"""
from typing import Optional, Dict
from src.database import (
    create_user, authenticate_user, validate_session, 
    delete_session, get_user_by_id, get_user_by_email,
    CLERK_AVAILABLE
)

class AuthService:
    """Authentication service - uses Clerk or local auth"""
    
    @staticmethod
    def register(email: str, password: str, name: str = None) -> Dict:
        """Register a new user (local auth only - Clerk handles its own registration)"""
        if not email or not password:
            return {"success": False, "error": "Email and password required"}
        
        if len(password) < 6:
            return {"success": False, "error": "Password must be at least 6 characters"}
        
        user_id = create_user(email, password, name)
        if user_id:
            # Auto-login after registration
            login_result = AuthService.login(email, password)
            if login_result["success"]:
                return login_result
            return {
                "success": True,
                "user_id": user_id,
                "email": email,
                "name": name,
                "token": None
            }
        return {"success": False, "error": "Email already registered"}
    
    @staticmethod
    def login(email: str, password: str) -> Dict:
        """Authenticate user and return session token"""
        user = authenticate_user(email, password)
        if user:
            return {
                "success": True,
                "user_id": user['id'],
                "email": user['email'],
                "name": user.get('name'),
                "is_admin": user.get('is_admin', False),
                "token": user.get('access_token')
            }
        return {"success": False, "error": "Invalid email or password"}
    
    @staticmethod
    def logout(token: str) -> Dict:
        """Invalidate session"""
        delete_session(token)
        return {"success": True}
    
    @staticmethod
    def validate_token(token: str) -> Optional[Dict]:
        """Validate session token and return user info"""
        if not token:
            return None
        return validate_session(token)
    
    @staticmethod
    def get_user(user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        return get_user_by_id(user_id)
    
    @staticmethod
    def get_user_email(email: str) -> Optional[Dict]:
        """Get user by email"""
        return get_user_by_email(email)
    
    @staticmethod
    def is_clerk_enabled() -> bool:
        """Check if Clerk is configured"""
        return CLERK_AVAILABLE
