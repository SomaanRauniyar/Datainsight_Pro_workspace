"""
User API Keys Management
Allows users to use their own API keys for Groq, Cohere, Pinecone
"""
import os
import json
import base64
from typing import Optional, Dict
from cryptography.fernet import Fernet
from src.database import supabase, SUPABASE_AVAILABLE

# Generate or load encryption key (in production, store this securely!)
# For now, derive from a secret or generate one
ENCRYPTION_KEY = os.getenv("API_KEY_ENCRYPTION_SECRET")
if not ENCRYPTION_KEY:
    # Fallback - in production, always set this env var!
    ENCRYPTION_KEY = "your-32-byte-secret-key-here!!"

# Ensure key is 32 bytes for Fernet
def get_fernet():
    key = ENCRYPTION_KEY.encode()[:32].ljust(32, b'0')
    return Fernet(base64.urlsafe_b64encode(key))

fernet = get_fernet()


def encrypt_key(api_key: str) -> str:
    """Encrypt an API key for storage"""
    return fernet.encrypt(api_key.encode()).decode()


def decrypt_key(encrypted_key: str) -> str:
    """Decrypt an API key from storage"""
    try:
        return fernet.decrypt(encrypted_key.encode()).decode()
    except:
        return ""


def save_user_key(user_id: str, key_name: str, key_value: str) -> bool:
    """Save an encrypted API key for a user"""
    if not SUPABASE_AVAILABLE:
        return False
    
    try:
        encrypted = encrypt_key(key_value)
        
        # Check if key already exists
        existing = supabase.table("user_api_keys").select("id").eq("user_id", user_id).eq("key_name", key_name).execute()
        
        if existing.data:
            # Update existing
            supabase.table("user_api_keys").update({
                "key_value": encrypted
            }).eq("user_id", user_id).eq("key_name", key_name).execute()
        else:
            # Insert new
            supabase.table("user_api_keys").insert({
                "user_id": user_id,
                "key_name": key_name,
                "key_value": encrypted
            }).execute()
        
        return True
    except Exception as e:
        print(f"[UserKeys] Save error: {e}")
        return False


def get_user_key(user_id: str, key_name: str) -> Optional[str]:
    """Get a decrypted API key for a user"""
    if not SUPABASE_AVAILABLE:
        return None
    
    try:
        result = supabase.table("user_api_keys").select("key_value").eq("user_id", user_id).eq("key_name", key_name).execute()
        
        if result.data:
            return decrypt_key(result.data[0]["key_value"])
    except Exception as e:
        print(f"[UserKeys] Get error: {e}")
    
    return None


def get_all_user_keys(user_id: str) -> Dict[str, bool]:
    """Get list of which keys a user has saved (not the actual values)"""
    if not SUPABASE_AVAILABLE:
        return {}
    
    try:
        result = supabase.table("user_api_keys").select("key_name").eq("user_id", user_id).execute()
        return {row["key_name"]: True for row in result.data} if result.data else {}
    except:
        return {}


def delete_user_key(user_id: str, key_name: str) -> bool:
    """Delete a user's API key"""
    if not SUPABASE_AVAILABLE:
        return False
    
    try:
        supabase.table("user_api_keys").delete().eq("user_id", user_id).eq("key_name", key_name).execute()
        return True
    except:
        return False


def get_effective_key(user_id: str, key_name: str, system_default: str = None) -> str:
    """
    Get the effective API key to use:
    1. Check if user has their own key → use it
    2. Otherwise → use system default from env
    """
    # Try user's key first
    user_key = get_user_key(user_id, key_name)
    if user_key:
        return user_key
    
    # Fall back to system key
    if system_default:
        return system_default
    
    # Map key names to env vars
    env_mapping = {
        "groq_api_key": "GROQ_API_KEY",
        "cohere_api_key": "COHERE_API_KEY",
        "pinecone_api_key": "PINECONE_API_KEY",
        "pinecone_index": "PINECONE_INDEX"
    }
    
    env_var = env_mapping.get(key_name)
    if env_var:
        return os.getenv(env_var, "")
    
    return ""


# ============== User Preferences (Model Selection) ==============
def save_user_preference(user_id: str, pref_name: str, pref_value: str) -> bool:
    """Save a user preference (like model selection)"""
    if not SUPABASE_AVAILABLE:
        return False
    
    try:
        # Check if preference exists
        existing = supabase.table("user_preferences").select("id").eq("user_id", user_id).eq("pref_name", pref_name).execute()
        
        if existing.data:
            supabase.table("user_preferences").update({
                "pref_value": pref_value
            }).eq("user_id", user_id).eq("pref_name", pref_name).execute()
        else:
            supabase.table("user_preferences").insert({
                "user_id": user_id,
                "pref_name": pref_name,
                "pref_value": pref_value
            }).execute()
        return True
    except Exception as e:
        print(f"[UserPrefs] Save error: {e}")
        return False


def get_user_preference(user_id: str, pref_name: str, default: str = None) -> str:
    """Get a user preference"""
    if not SUPABASE_AVAILABLE:
        return default
    
    try:
        result = supabase.table("user_preferences").select("pref_value").eq("user_id", user_id).eq("pref_name", pref_name).execute()
        if result.data:
            return result.data[0]["pref_value"]
    except:
        pass
    return default


def get_all_user_preferences(user_id: str) -> Dict[str, str]:
    """Get all preferences for a user"""
    if not SUPABASE_AVAILABLE:
        return {}
    
    try:
        result = supabase.table("user_preferences").select("pref_name, pref_value").eq("user_id", user_id).execute()
        return {row["pref_name"]: row["pref_value"] for row in result.data} if result.data else {}
    except:
        return {}


def test_groq_key(api_key: str) -> Dict:
    """Test if a Groq API key is valid"""
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        # Make a minimal request
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        return {"valid": True, "message": "Groq API key is valid!"}
    except Exception as e:
        return {"valid": False, "message": f"Invalid key: {str(e)[:50]}"}


def test_cohere_key(api_key: str) -> Dict:
    """Test if a Cohere API key is valid"""
    try:
        import cohere
        client = cohere.Client(api_key)
        # Make a minimal embed request
        response = client.embed(texts=["test"], model="embed-english-v3.0", input_type="search_document")
        return {"valid": True, "message": "Cohere API key is valid!"}
    except Exception as e:
        return {"valid": False, "message": f"Invalid key: {str(e)[:50]}"}


def test_pinecone_key(api_key: str, index_name: str = None) -> Dict:
    """Test if a Pinecone API key is valid"""
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=api_key)
        # List indexes to verify key
        indexes = pc.list_indexes()
        
        if index_name:
            index_names = [idx.name for idx in indexes]
            if index_name not in index_names:
                return {"valid": True, "message": f"Key valid, but index '{index_name}' not found. Available: {index_names}"}
        
        return {"valid": True, "message": "Pinecone API key is valid!"}
    except Exception as e:
        return {"valid": False, "message": f"Invalid key: {str(e)[:50]}"}


def test_api_key(user_id: str, key_name: str) -> Dict:
    """Test a user's saved API key"""
    key_value = get_user_key(user_id, key_name)
    
    if not key_value:
        return {"valid": False, "message": "No key saved"}
    
    if key_name == "groq_api_key":
        return test_groq_key(key_value)
    elif key_name == "cohere_api_key":
        return test_cohere_key(key_value)
    elif key_name == "pinecone_api_key":
        # Also get index name if available
        index_name = get_user_key(user_id, "pinecone_index")
        return test_pinecone_key(key_value, index_name)
    elif key_name == "pinecone_index":
        # Test with pinecone key
        pinecone_key = get_user_key(user_id, "pinecone_api_key")
        if pinecone_key:
            return test_pinecone_key(pinecone_key, key_value)
        return {"valid": False, "message": "Add Pinecone API key first"}
    
    return {"valid": False, "message": "Unknown key type"}
