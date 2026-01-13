"""
Authentication Routes - User registration, login, and session management
"""
from fastapi import APIRouter, HTTPException, Header, Request
from typing import Optional
import requests as http_requests
import secrets
import base64
import json as json_lib
import os

from src.auth import AuthService
from src.database import store_clerk_session
from src.security import sanitize_email, sanitize_string, check_rate_limit, validate_password_strength
from ..models import (
    RegisterRequest, LoginRequest, ClerkSignInRequest, 
    ClerkSignUpRequest, ClerkCallbackRequest
)
from ..dependencies import get_current_user, require_auth

router = APIRouter()

@router.post("/register")
def register(req: RegisterRequest):
    """Register new user with email and password"""
    # Security: Validate and sanitize email
    email = sanitize_email(req.email)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Security: Validate password strength
    is_valid, error_msg = validate_password_strength(req.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Security: Sanitize name
    name = sanitize_string(req.name, max_length=100) if req.name else None
    
    result = AuthService.register(email, req.password, name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/login")
def login(req: LoginRequest, request: Request):
    """Login with email and password"""
    # Security: Rate limit login attempts per IP
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"login:{client_ip}", max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please wait.")
    
    # Security: Validate email format
    email = sanitize_email(req.email)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    result = AuthService.login(email, req.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    """Logout and invalidate session token"""
    if authorization:
        token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
        AuthService.logout(token)
    return {"success": True}

@router.get("/me")
def get_me(user: dict = require_auth):
    """Get current user information"""
    return user

# ============== Clerk Authentication ==============

@router.post("/clerk-signin")
def clerk_signin(req: ClerkSignInRequest):
    """Sign in user via Clerk Backend API"""
    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
    if not CLERK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Clerk not configured")
    
    headers = {
        "Authorization": f"Bearer {CLERK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Find user by email
        resp = http_requests.get(
            "https://api.clerk.com/v1/users",
            headers=headers,
            params={"email_address": req.email.lower()}
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        users = resp.json()
        if not users:
            raise HTTPException(status_code=401, detail="User not found. Please sign up first.")
        
        user = users[0]
        user_id = user.get("id")
        
        # Verify password
        verify_resp = http_requests.post(
            f"https://api.clerk.com/v1/users/{user_id}/verify_password",
            headers=headers,
            json={"password": req.password}
        )
        
        if verify_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid password")
        
        verify_data = verify_resp.json()
        if not verify_data.get("verified"):
            raise HTTPException(status_code=401, detail="Invalid password")
        
        # Get user email
        email = ""
        email_addresses = user.get("email_addresses", [])
        for addr in email_addresses:
            if addr.get("id") == user.get("primary_email_address_id"):
                email = addr.get("email_address", "")
                break
        if not email and email_addresses:
            email = email_addresses[0].get("email_address", "")
        
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        
        # Store session
        store_clerk_session(session_token, user_id, email, 
                           f"{user.get('first_name', '')} {user.get('last_name', '')}".strip())
        
        return {
            "success": True,
            "user_id": user_id,
            "email": email,
            "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or email.split('@')[0],
            "is_admin": False,
            "token": session_token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

@router.post("/clerk-signup")
def clerk_signup(req: ClerkSignUpRequest):
    """Create new user in Clerk"""
    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
    if not CLERK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Clerk not configured")
    
    headers = {
        "Authorization": f"Bearer {CLERK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    # Validate password length
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    try:
        # Check if user already exists
        check_resp = http_requests.get(
            "https://api.clerk.com/v1/users",
            headers=headers,
            params={"email_address": req.email.lower()}
        )
        
        if check_resp.status_code == 200:
            existing = check_resp.json()
            if existing:
                raise HTTPException(status_code=400, detail="Email already registered. Please sign in.")
        
        # Create user in Clerk
        name_parts = (req.name or req.email.split('@')[0]).split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        create_resp = http_requests.post(
            "https://api.clerk.com/v1/users",
            headers=headers,
            json={
                "email_address": [req.email.lower()],
                "password": req.password,
                "first_name": first_name,
                "last_name": last_name,
                "skip_password_checks": False,
                "skip_password_requirement": False
            }
        )
        
        if create_resp.status_code not in [200, 201]:
            error_data = create_resp.json()
            error_msg = error_data.get("errors", [{}])[0].get("message", "Failed to create account")
            raise HTTPException(status_code=400, detail=error_msg)
        
        user = create_resp.json()
        user_id = user.get("id")
        
        # Get email from response
        email = req.email.lower()
        email_addresses = user.get("email_addresses", [])
        if email_addresses:
            email = email_addresses[0].get("email_address", email)
        
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        
        # Store session
        store_clerk_session(session_token, user_id, email,
                           f"{user.get('first_name', '')} {user.get('last_name', '')}".strip())
        
        return {
            "success": True,
            "user_id": user_id,
            "email": email,
            "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or email.split('@')[0],
            "is_admin": False,
            "token": session_token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup error: {str(e)}")

@router.post("/clerk-callback")
def clerk_callback(req: ClerkCallbackRequest):
    """Handle Clerk authentication callback (legacy)"""
    from src.clerk_auth import get_user, is_configured
    
    if not is_configured():
        raise HTTPException(status_code=500, detail="Clerk not configured")
    
    try:
        # Decode JWT payload
        parts = req.session_token.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            try:
                decoded = base64.urlsafe_b64decode(payload)
                token_data = json_lib.loads(decoded)
                user_id = token_data.get("sub") or token_data.get("user_id")
                
                if user_id:
                    user_info = get_user(user_id)
                    if user_info:
                        return {
                            "success": True,
                            "user_id": user_info["id"],
                            "email": user_info["email"],
                            "name": user_info.get("name", ""),
                            "is_admin": False,
                            "token": req.session_token
                        }
            except:
                pass
        
        raise HTTPException(status_code=401, detail="Invalid session token")
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")