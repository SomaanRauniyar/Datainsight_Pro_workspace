"""
Clerk Authentication for DataInsight Pro
Full Clerk integration for production-ready auth
"""
import os
import requests
from typing import Optional, Dict, List
from pathlib import Path
from dotenv import load_dotenv

# Load env
for p in [Path(__file__).parent.parent / ".env", Path.cwd() / ".env"]:
    if p.exists():
        load_dotenv(p, override=True)
        break

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")
CLERK_API_URL = "https://api.clerk.com/v1"

def is_configured() -> bool:
    """Check if Clerk is configured"""
    return bool(CLERK_SECRET_KEY and CLERK_PUBLISHABLE_KEY)

def _headers() -> Dict:
    """Get auth headers for Clerk API"""
    return {
        "Authorization": f"Bearer {CLERK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

def verify_session_token(token: str) -> Optional[Dict]:
    """
    Verify a Clerk session token (from frontend)
    Returns user info if valid
    """
    if not CLERK_SECRET_KEY:
        return None
    
    try:
        # For Clerk, we verify JWT tokens
        # The token from frontend is a session token
        resp = requests.post(
            f"{CLERK_API_URL}/tokens/verify",
            headers=_headers(),
            json={"token": token}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            user_id = data.get("sub") or data.get("user_id")
            if user_id:
                return get_user(user_id)
    except Exception as e:
        print(f"Token verify error: {e}")
    
    return None

def get_user(user_id: str) -> Optional[Dict]:
    """Get user details from Clerk"""
    if not CLERK_SECRET_KEY:
        return None
    
    try:
        resp = requests.get(
            f"{CLERK_API_URL}/users/{user_id}",
            headers=_headers()
        )
        
        if resp.status_code == 200:
            data = resp.json()
            
            # Get primary email
            email = ""
            email_addresses = data.get("email_addresses", [])
            for addr in email_addresses:
                if addr.get("id") == data.get("primary_email_address_id"):
                    email = addr.get("email_address", "")
                    break
            if not email and email_addresses:
                email = email_addresses[0].get("email_address", "")
            
            return {
                "id": data.get("id"),
                "user_id": data.get("id"),
                "email": email,
                "name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or email.split('@')[0],
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "image_url": data.get("image_url"),
                "is_admin": False,
                "created_at": data.get("created_at")
            }
    except Exception as e:
        print(f"Get user error: {e}")
    
    return None

def get_user_by_email(email: str) -> Optional[Dict]:
    """Find user by email"""
    if not CLERK_SECRET_KEY:
        return None
    
    try:
        resp = requests.get(
            f"{CLERK_API_URL}/users",
            headers=_headers(),
            params={"email_address": email}
        )
        
        if resp.status_code == 200:
            users = resp.json()
            if users and len(users) > 0:
                return get_user(users[0]["id"])
    except:
        pass
    
    return None

def list_users(limit: int = 100) -> List[Dict]:
    """List all users (admin)"""
    if not CLERK_SECRET_KEY:
        return []
    
    try:
        resp = requests.get(
            f"{CLERK_API_URL}/users",
            headers=_headers(),
            params={"limit": limit}
        )
        
        if resp.status_code == 200:
            users = resp.json()
            return [
                {
                    "id": u.get("id"),
                    "email": u.get("email_addresses", [{}])[0].get("email_address", ""),
                    "name": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip(),
                    "created_at": u.get("created_at"),
                    "last_sign_in": u.get("last_sign_in_at")
                }
                for u in users
            ]
    except:
        pass
    
    return []

def get_user_count() -> int:
    """Get total user count"""
    if not CLERK_SECRET_KEY:
        return 0
    
    try:
        resp = requests.get(
            f"{CLERK_API_URL}/users/count",
            headers=_headers()
        )
        if resp.status_code == 200:
            return resp.json().get("total_count", 0)
    except:
        pass
    
    return 0

# Check configuration on import
if is_configured():
    print("✅ Clerk authentication configured")
else:
    print("⚠️ Clerk not configured - set CLERK_SECRET_KEY and CLERK_PUBLISHABLE_KEY")
