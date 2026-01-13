"""
Gmail API Service for Team Chat
Handles OAuth, sending emails, and reading threads
"""
import os
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load env
for p in [Path(__file__).parent.parent / ".env", Path.cwd() / ".env"]:
    if p.exists():
        load_dotenv(p, override=True)
        break

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API Configuration
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_REDIRECT_URI = os.getenv("GMAIL_REDIRECT_URI", "http://localhost:8000/auth/gmail/callback")

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Store user tokens (in production, store in database)
_user_tokens = {}

def is_configured() -> bool:
    """Check if Gmail API is configured"""
    return bool(GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET)

def get_oauth_flow() -> Flow:
    """Create OAuth flow for Gmail"""
    client_config = {
        "web": {
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GMAIL_REDIRECT_URI]
        }
    }
    
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = GMAIL_REDIRECT_URI
    return flow

def get_auth_url(state: str = None) -> str:
    """Get Gmail OAuth authorization URL"""
    if not is_configured():
        return None
    
    flow = get_oauth_flow()
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=state
    )
    return auth_url

def exchange_code_for_tokens(code: str) -> Optional[Dict]:
    """Exchange authorization code for tokens"""
    if not is_configured():
        return None
    
    try:
        flow = get_oauth_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        return {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes)
        }
    except Exception as e:
        print(f"Token exchange error: {e}")
        return None

def store_user_tokens(user_id: str, tokens: Dict):
    """Store user's Gmail tokens"""
    _user_tokens[user_id] = tokens
    
    # Also store in Supabase for persistence
    try:
        from src.database import supabase, SUPABASE_AVAILABLE
        if SUPABASE_AVAILABLE:
            # Check if session exists
            existing = supabase.table("user_sessions").select("*").eq("user_id", user_id).execute()
            if existing.data:
                # Update existing session
                supabase.table("user_sessions").update({
                    "gmail_tokens": json.dumps(tokens)
                }).eq("user_id", user_id).execute()
            else:
                # Create new session with gmail tokens
                supabase.table("user_sessions").insert({
                    "user_id": user_id,
                    "gmail_tokens": json.dumps(tokens)
                }).execute()
            print(f"✅ Gmail tokens saved for user {user_id}")
    except Exception as e:
        print(f"⚠️ Failed to save Gmail tokens to Supabase: {e}")

def get_user_tokens(user_id: str) -> Optional[Dict]:
    """Get user's Gmail tokens"""
    if user_id in _user_tokens:
        return _user_tokens[user_id]
    
    # Try to load from Supabase
    try:
        from src.database import supabase, SUPABASE_AVAILABLE
        if SUPABASE_AVAILABLE:
            result = supabase.table("user_sessions").select("gmail_tokens").eq("user_id", user_id).execute()
            if result.data and result.data[0].get("gmail_tokens"):
                tokens = json.loads(result.data[0]["gmail_tokens"])
                _user_tokens[user_id] = tokens
                return tokens
    except:
        pass
    
    return None

def get_gmail_service(user_id: str):
    """Get authenticated Gmail service for user"""
    tokens = get_user_tokens(user_id)
    if not tokens:
        return None
    
    try:
        credentials = Credentials(
            token=tokens.get("token"),
            refresh_token=tokens.get("refresh_token"),
            token_uri=tokens.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=tokens.get("client_id", GMAIL_CLIENT_ID),
            client_secret=tokens.get("client_secret", GMAIL_CLIENT_SECRET),
            scopes=tokens.get("scopes", SCOPES)
        )
        
        service = build('gmail', 'v1', credentials=credentials)
        return service
    except Exception as e:
        print(f"Gmail service error: {e}")
        return None

def is_user_connected(user_id: str) -> bool:
    """Check if user has connected Gmail"""
    return get_user_tokens(user_id) is not None

def get_user_email(user_id: str) -> Optional[str]:
    """Get user's Gmail address"""
    service = get_gmail_service(user_id)
    if not service:
        return None
    
    try:
        profile = service.users().getProfile(userId='me').execute()
        return profile.get('emailAddress')
    except:
        return None

def send_email(user_id: str, to: List[str], subject: str, body: str, 
               cc: List[str] = None, thread_id: str = None) -> Optional[Dict]:
    """
    Send email via Gmail API
    Returns: {"message_id": str, "thread_id": str} or None
    """
    service = get_gmail_service(user_id)
    if not service:
        return None
    
    try:
        # Create message
        message = MIMEMultipart()
        message['to'] = ', '.join(to)
        message['subject'] = subject
        
        if cc:
            message['cc'] = ', '.join(cc)
        
        # Add body
        message.attach(MIMEText(body, 'plain'))
        
        # Encode
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        body_data = {'raw': raw}
        if thread_id:
            body_data['threadId'] = thread_id
        
        # Send
        sent = service.users().messages().send(userId='me', body=body_data).execute()
        
        return {
            "message_id": sent.get('id'),
            "thread_id": sent.get('threadId')
        }
    except HttpError as e:
        print(f"Gmail send error: {e}")
        return None

def send_group_message(user_id: str, group_members: List[str], subject: str, 
                       body: str, thread_id: str = None) -> Optional[Dict]:
    """
    Send message to all group members (CC all)
    """
    if not group_members:
        return None
    
    # First member is 'to', rest are 'cc'
    to = [group_members[0]]
    cc = group_members[1:] if len(group_members) > 1 else []
    
    return send_email(user_id, to, subject, body, cc, thread_id)

def get_thread_messages(user_id: str, thread_id: str) -> List[Dict]:
    """Get all messages in a thread"""
    service = get_gmail_service(user_id)
    if not service:
        return []
    
    try:
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        messages = []
        
        for msg in thread.get('messages', []):
            msg_data = parse_message(msg)
            if msg_data:
                messages.append(msg_data)
        
        return messages
    except HttpError as e:
        print(f"Gmail thread error: {e}")
        return []

def parse_message(msg: Dict) -> Optional[Dict]:
    """Parse Gmail message into readable format"""
    try:
        headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
        
        # Get body
        body = ""
        payload = msg['payload']
        
        if 'body' in payload and payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        
        return {
            "id": msg['id'],
            "thread_id": msg['threadId'],
            "from": headers.get('From', ''),
            "to": headers.get('To', ''),
            "cc": headers.get('Cc', ''),
            "subject": headers.get('Subject', ''),
            "date": headers.get('Date', ''),
            "body": body,
            "timestamp": int(msg.get('internalDate', 0)) // 1000
        }
    except Exception as e:
        print(f"Parse message error: {e}")
        return None

def check_new_messages(user_id: str, after_timestamp: int = None) -> List[Dict]:
    """Check for new messages (for polling)"""
    service = get_gmail_service(user_id)
    if not service:
        return []
    
    try:
        query = "in:inbox"
        if after_timestamp:
            query += f" after:{after_timestamp}"
        
        results = service.users().messages().list(
            userId='me', q=query, maxResults=20
        ).execute()
        
        messages = []
        for msg_ref in results.get('messages', []):
            msg = service.users().messages().get(userId='me', id=msg_ref['id']).execute()
            parsed = parse_message(msg)
            if parsed:
                messages.append(parsed)
        
        return messages
    except HttpError as e:
        print(f"Gmail check error: {e}")
        return []

# Check configuration on import
if is_configured():
    print("✅ Gmail API configured")
else:
    print("⚠️ Gmail API not configured - set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET")
