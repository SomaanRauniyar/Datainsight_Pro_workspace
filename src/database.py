"""
Database module for DataInsight Pro
Uses Supabase for persistent storage, falls back to in-memory
"""
import os
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv

# Load env
for p in [Path(__file__).parent.parent / ".env", Path.cwd() / ".env"]:
    if p.exists():
        load_dotenv(p, override=True)
        break

# Clerk configuration
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")
CLERK_API_URL = "https://api.clerk.com/v1"
CLERK_AVAILABLE = bool(CLERK_SECRET_KEY)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase = None
SUPABASE_AVAILABLE = False

try:
    from supabase import create_client, Client
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        SUPABASE_AVAILABLE = True
except ImportError:
    pass

# In-memory fallback storage
_memory_store = {
    "users": {}, "teams": {}, "team_members": {}, "token_usage": [],
    "files": [], "briefings": [], "email_threads": {}, "email_messages": {},
    "clerk_sessions": {}
}

def retry_supabase_query(func, max_retries=3, delay=0.5):
    """Retry Supabase queries on temporary connection failures"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            error_msg = str(e).lower()
            # Retry on connection issues
            if "resource temporarily unavailable" in error_msg or "connection" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
                    continue
            raise  # Re-raise if not a connection issue or max retries reached
    return None

def init_db():
    if CLERK_AVAILABLE:
        print("Clerk auth configured")
    if SUPABASE_AVAILABLE:
        print("Supabase database connected")
    else:
        print("Using in-memory storage (data won't persist)")


# ============== Session Management ==============
def store_clerk_session(token: str, user_id: str, email: str, name: str = None):
    print(f"[DEBUG] Storing session for user: {email}")
    
    if SUPABASE_AVAILABLE:
        try:
            # Delete old sessions for this user
            supabase.table("user_sessions").delete().eq("user_id", user_id).execute()
            # Insert new session
            result = supabase.table("user_sessions").insert({
                "token": token, "user_id": user_id, "email": email,
                "name": name, "is_admin": False
            }).execute()
            print(f"[DEBUG] Supabase session stored successfully")
            return
        except Exception as e:
            print(f"[ERROR] Supabase session storage failed: {e}")
    
    # Always store in memory as backup
    if "clerk_sessions" not in _memory_store:
        _memory_store["clerk_sessions"] = {}
    
    _memory_store["clerk_sessions"][token] = {
        "user_id": user_id, "email": email, "name": name,
        "is_admin": False, "created_at": datetime.now().isoformat()
    }
    print(f"[DEBUG] Memory session stored for {email}")

def validate_session(token: str) -> Optional[Dict]:
    if not token:
        return None
    
    print(f"[DEBUG] Validating token: {token[:20]}...")
    
    if SUPABASE_AVAILABLE:
        try:
            def query():
                return supabase.table("user_sessions").select("*").eq("token", token).execute()
            
            result = retry_supabase_query(query)
            if result and result.data:
                s = result.data[0]
                print(f"[DEBUG] ✅ Supabase validation successful for user: {s.get('email')}")
                return {"user_id": s["user_id"], "email": s["email"], 
                        "name": s.get("name"), "is_admin": s.get("is_admin", False)}
        except Exception as e:
            print(f"[ERROR] ❌ Supabase validate error: {e}")
            print(f"[WARNING] 🔄 Falling back to memory store...")
    
    # Check Clerk sessions
    if token in _memory_store.get("clerk_sessions", {}):
        s = _memory_store["clerk_sessions"][token]
        print(f"[DEBUG] ✅ Clerk session validation successful for user: {s.get('email')}")
        return {"user_id": s["user_id"], "email": s["email"],
                "name": s.get("name"), "is_admin": s.get("is_admin", False)}
    
    # Check local users
    for user in _memory_store["users"].values():
        if user.get("token") == token:
            print(f"[DEBUG] ✅ Local user validation successful for user: {user.get('email')}")
            return {"user_id": user["id"], "email": user["email"],
                    "name": user.get("name"), "is_admin": user.get("is_admin", False)}
    
    print(f"[ERROR] ❌ Token validation failed - no matching session found")
    return None

def delete_session(token: str):
    if SUPABASE_AVAILABLE:
        try:
            supabase.table("user_sessions").delete().eq("token", token).execute()
        except:
            pass
    if token in _memory_store.get("clerk_sessions", {}):
        del _memory_store["clerk_sessions"][token]


# ============== Team Operations ==============
def create_team(owner_id: str, name: str) -> Optional[int]:
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("teams").insert({"owner_id": owner_id, "name": name}).execute()
            if result.data:
                return result.data[0]["id"]
        except:
            pass
    team_id = len(_memory_store["teams"]) + 1
    _memory_store["teams"][team_id] = {"id": team_id, "owner_id": owner_id, "name": name}
    _memory_store["team_members"][team_id] = []
    return team_id

def get_user_team(user_id: str) -> Optional[Dict]:
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("teams").select("*").eq("owner_id", user_id).execute()
            if result.data:
                team = result.data[0]
                members_result = supabase.table("team_members").select("email").eq("team_id", team["id"]).execute()
                members = [m["email"] for m in members_result.data] if members_result.data else []
                return {"team_id": team["id"], "name": team["name"], "members": members}
        except:
            pass
    for team in _memory_store["teams"].values():
        if team["owner_id"] == user_id:
            return {"team_id": team["id"], "name": team["name"], 
                    "members": _memory_store["team_members"].get(team["id"], [])}
    return None

def add_team_member(team_id: int, email: str) -> bool:
    email = email.lower()
    if SUPABASE_AVAILABLE:
        try:
            supabase.table("team_members").insert({"team_id": team_id, "email": email}).execute()
            return True
        except:
            return False
    if team_id not in _memory_store["team_members"]:
        _memory_store["team_members"][team_id] = []
    if email not in _memory_store["team_members"][team_id]:
        _memory_store["team_members"][team_id].append(email)
        return True
    return False

def remove_team_member(team_id: int, email: str) -> bool:
    if SUPABASE_AVAILABLE:
        try:
            supabase.table("team_members").delete().eq("team_id", team_id).eq("email", email.lower()).execute()
            return True
        except:
            return False
    if team_id in _memory_store["team_members"] and email.lower() in _memory_store["team_members"][team_id]:
        _memory_store["team_members"][team_id].remove(email.lower())
        return True
    return False

def get_team_members(team_id: int) -> List[str]:
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("team_members").select("email").eq("team_id", team_id).execute()
            return [m["email"] for m in result.data] if result.data else []
        except:
            pass
    return _memory_store["team_members"].get(team_id, [])


# ============== Token Usage ==============
def log_token_usage(user_id: str, tokens: int, operation: str = None):
    if SUPABASE_AVAILABLE:
        try:
            supabase.table("token_usage").insert({
                "user_id": user_id, "tokens": tokens, "operation": operation
            }).execute()
            return
        except:
            pass
    _memory_store["token_usage"].append({
        "user_id": user_id, "tokens": tokens, "operation": operation,
        "timestamp": datetime.now().isoformat()
    })

def get_user_token_usage(user_id: str, days: int = 30) -> int:
    cutoff = datetime.now() - timedelta(days=days)
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("token_usage").select("tokens").eq("user_id", user_id).gte("timestamp", cutoff.isoformat()).execute()
            return sum(r["tokens"] for r in result.data) if result.data else 0
        except:
            pass
    total = 0
    for entry in _memory_store["token_usage"]:
        if entry["user_id"] == user_id:
            try:
                if datetime.fromisoformat(entry["timestamp"]) > cutoff:
                    total += entry["tokens"]
            except:
                total += entry["tokens"]
    return total

# ============== File Tracking ==============
def track_file_upload(user_id: str, filename: str, file_type: str, summary: str = None) -> int:
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("file_uploads").insert({
                "user_id": user_id, "filename": filename, 
                "file_type": file_type, "summary": summary
            }).execute()
            if result.data:
                return result.data[0]["id"]
        except Exception as e:
            print(f"File upload tracking error: {e}")
    file_id = len(_memory_store["files"]) + 1
    _memory_store["files"].append({
        "id": file_id, "user_id": user_id, "filename": filename,
        "file_type": file_type, "summary": summary,
        "upload_time": datetime.now().isoformat()
    })
    return file_id

def get_user_files(user_id: str) -> List[Dict]:
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("file_uploads").select("*").eq("user_id", user_id).order("upload_time", desc=True).execute()
            return result.data if result.data else []
        except:
            pass
    return [f for f in _memory_store["files"] if f["user_id"] == user_id]


# ============== Briefings ==============
def save_briefing(user_id: str, content, briefing_type: str, file_id: int = None) -> int:
    import json
    content_data = content if isinstance(content, (dict, list)) else {"text": str(content)}
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("briefings").insert({
                "user_id": user_id, "file_id": file_id,
                "briefing_type": briefing_type, "content": content_data
            }).execute()
            if result.data:
                return result.data[0]["id"]
        except Exception as e:
            print(f"Briefing save error: {e}")
    brief_id = len(_memory_store["briefings"]) + 1
    _memory_store["briefings"].append({
        "id": brief_id, "user_id": user_id, "file_id": file_id,
        "briefing_type": briefing_type, "content": content_data,
        "created_at": datetime.now().isoformat()
    })
    return brief_id

def get_briefings(user_id: str, briefing_type: str = None) -> List[Dict]:
    if SUPABASE_AVAILABLE:
        try:
            query = supabase.table("briefings").select("*").eq("user_id", user_id)
            if briefing_type:
                query = query.eq("briefing_type", briefing_type)
            result = query.order("created_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Get briefings error: {e}")
    results = [b for b in _memory_store["briefings"] if b["user_id"] == user_id]
    if briefing_type:
        results = [b for b in results if b["briefing_type"] == briefing_type]
    return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)

def delete_briefing_by_id(briefing_id: int, user_id: str) -> bool:
    """Delete a briefing by ID (only if owned by user)"""
    if SUPABASE_AVAILABLE:
        try:
            # First verify ownership
            check = supabase.table("briefings").select("id").eq("id", briefing_id).eq("user_id", user_id).execute()
            if not check.data:
                return False
            # Delete
            supabase.table("briefings").delete().eq("id", briefing_id).execute()
            return True
        except Exception as e:
            print(f"Delete briefing error: {e}")
            return False
    # In-memory fallback
    for i, b in enumerate(_memory_store["briefings"]):
        if b.get("id") == briefing_id and b.get("user_id") == user_id:
            _memory_store["briefings"].pop(i)
            return True
    return False


# ============== Email Threads ==============
def get_email_threads(user_id: str, limit: int = 20) -> List[Dict]:
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("email_threads").select("*").eq("user_id", user_id).order("last_updated", desc=True).limit(limit).execute()
            return result.data if result.data else []
        except:
            pass
    threads = _memory_store["email_threads"].get(user_id, [])
    for t in threads:
        t['message_count'] = len(_memory_store["email_messages"].get(t['id'], []))
    return threads[:limit]

def create_email_thread(user_id: str, subject: str, thread_id: str = None, contact: str = None) -> int:
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("email_threads").insert({
                "user_id": user_id, "thread_id": thread_id,
                "subject": subject, "contact": contact or ""
            }).execute()
            if result.data:
                return result.data[0]["id"]
        except:
            pass
    if user_id not in _memory_store["email_threads"]:
        _memory_store["email_threads"][user_id] = []
    tid = len(_memory_store["email_threads"][user_id]) + 1
    _memory_store["email_threads"][user_id].append({
        "id": tid, "thread_id": thread_id or f"thread_{tid}",
        "subject": subject, "contact": contact or "",
        "last_updated": datetime.now().isoformat()
    })
    _memory_store["email_messages"][tid] = []
    return tid

def get_or_create_contact_thread(user_id: str, contact: str, subject: str = None) -> int:
    contact_lower = contact.lower()
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("email_threads").select("id").eq("user_id", user_id).ilike("contact", contact_lower).execute()
            if result.data:
                thread_id = result.data[0]["id"]
                supabase.table("email_threads").update({"last_updated": datetime.now().isoformat()}).eq("id", thread_id).execute()
                return thread_id
        except:
            pass
    else:
        if user_id in _memory_store["email_threads"]:
            for thread in _memory_store["email_threads"][user_id]:
                if thread.get("contact", "").lower() == contact_lower:
                    thread["last_updated"] = datetime.now().isoformat()
                    return thread["id"]
    return create_email_thread(user_id, subject or f"Chat with {contact.split('@')[0].title()}", contact=contact)

def add_email_message(thread_id: int, sender: str, recipients: str, body: str, is_from_user: bool = False, chart_json: str = None) -> int:
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("email_messages").insert({
                "thread_id": thread_id, "sender": sender, "recipients": recipients,
                "body": body, "is_from_user": is_from_user, "chart_json": chart_json
            }).execute()
            supabase.table("email_threads").update({"last_updated": datetime.now().isoformat()}).eq("id", thread_id).execute()
            if result.data:
                return result.data[0]["id"]
        except:
            pass
    if thread_id not in _memory_store["email_messages"]:
        _memory_store["email_messages"][thread_id] = []
    msg_id = len(_memory_store["email_messages"][thread_id]) + 1
    _memory_store["email_messages"][thread_id].append({
        "id": msg_id, "sender": sender, "recipients": recipients,
        "body": body, "is_from_user": is_from_user, "chart_json": chart_json,
        "sent_at": datetime.now().isoformat()
    })
    return msg_id

def get_thread_messages(thread_id: int) -> List[Dict]:
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("email_messages").select("*").eq("thread_id", thread_id).order("sent_at").execute()
            return result.data if result.data else []
        except:
            pass
    return _memory_store["email_messages"].get(thread_id, [])

def add_shared_chart(user_id: str, chart_json: str, title: str) -> int:
    thread_id = get_or_create_contact_thread(user_id, "team", "Shared Charts")
    return add_email_message(thread_id, "You", "Team", f"Chart: {title}", True, chart_json)


# ============== Admin Functions ==============
def get_all_users() -> List[Dict]:
    if SUPABASE_AVAILABLE:
        try:
            result = supabase.table("user_sessions").select("user_id, email, name").execute()
            seen = set()
            users = []
            for u in result.data or []:
                if u["user_id"] not in seen:
                    seen.add(u["user_id"])
                    users.append({"id": u["user_id"], "email": u["email"], "name": u.get("name")})
            return users
        except:
            pass
    return [{"id": u["id"], "email": u["email"], "name": u.get("name")} for u in _memory_store["users"].values()]

def get_system_stats() -> Dict:
    if SUPABASE_AVAILABLE:
        try:
            users = supabase.table("user_sessions").select("user_id", count="exact").execute()
            tokens = supabase.table("token_usage").select("tokens").execute()
            files = supabase.table("file_uploads").select("id", count="exact").execute()
            return {
                "active_users": users.count or 0,
                "total_tokens": sum(t["tokens"] for t in tokens.data) if tokens.data else 0,
                "total_files": files.count or 0
            }
        except:
            pass
    return {
        "active_users": len(_memory_store["users"]),
        "total_tokens": sum(e["tokens"] for e in _memory_store["token_usage"]),
        "total_files": len(_memory_store["files"])
    }

# ============== Local Auth (Fallback) ==============
import hashlib
import secrets

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{pwd_hash.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, pwd_hash = stored_hash.split(':')
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return new_hash.hex() == pwd_hash
    except:
        return False

def create_user(email: str, password: str, name: str = None) -> Optional[str]:
    email = email.lower()
    if email in _memory_store["users"]:
        return None
    user_id = secrets.token_hex(16)
    _memory_store["users"][email] = {
        "id": user_id, "email": email, "name": name,
        "password_hash": hash_password(password), "is_admin": False
    }
    return user_id

def authenticate_user(email: str, password: str) -> Optional[Dict]:
    email = email.lower()
    user = _memory_store["users"].get(email)
    if user and verify_password(password, user["password_hash"]):
        token = secrets.token_urlsafe(32)
        user["token"] = token
        return {"id": user["id"], "email": user["email"], "name": user.get("name"),
                "is_admin": user.get("is_admin", False), "access_token": token}
    return None

def get_user_by_id(user_id: str) -> Optional[Dict]:
    for user in _memory_store["users"].values():
        if user["id"] == user_id:
            return {"id": user["id"], "email": user["email"], 
                    "name": user.get("name"), "is_admin": user.get("is_admin", False)}
    return None

def get_user_by_email(email: str) -> Optional[Dict]:
    user = _memory_store["users"].get(email.lower())
    if user:
        return {"id": user["id"], "email": user["email"],
                "name": user.get("name"), "is_admin": user.get("is_admin", False)}
    return None

# Initialize
init_db()
