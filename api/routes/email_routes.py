"""
Email Routes - Gmail integration and team communication
"""
from fastapi import APIRouter, Query, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse
from typing import Optional
import base64
import os

from src.email_service import get_email_service
from src.team_manager import TeamManager
from src.gmail_service import (
    get_auth_url as gmail_get_auth_url, exchange_code_for_tokens,
    store_user_tokens, is_user_connected as gmail_is_connected,
    get_user_email as gmail_get_user_email, is_configured as gmail_is_configured
)
from ..dependencies import require_auth
from ..models import SendEmailRequest, ReplyEmailRequest, EmailShareChartRequest, GmailTokensRequest

router = APIRouter()

@router.get("/status")
def get_email_status(user: dict = Depends(require_auth)):
    """Check email connection status"""
    service = get_email_service(user["user_id"])
    return {
        "connected": service.is_connected(),
        "type": "gmail" if hasattr(service, 'credentials') else "mock"
    }

@router.get("/auth-url")
def get_email_auth_url(user: dict = Depends(require_auth)):
    """Get Gmail OAuth URL - not implemented yet"""
    return {"auth_url": None, "message": "Gmail OAuth not configured"}

@router.get("/threads")
def get_email_threads(
    max_results: int = Query(20),
    user: dict = Depends(require_auth)
):
    """Get email threads"""
    service = get_email_service(user["user_id"])
    threads = service.get_threads(max_results)
    return {"threads": threads}

@router.get("/thread/{thread_id}")
def get_thread_messages(
    thread_id: str,
    user: dict = Depends(require_auth)
):
    """Get messages in a thread"""
    service = get_email_service(user["user_id"])
    messages = service.get_thread_messages(thread_id)
    return {"messages": messages}

@router.post("/send")
def send_email(
    req: SendEmailRequest,
    user: dict = Depends(require_auth)
):
    """Send email with optional team CC"""
    service = get_email_service(user["user_id"])
    result = service.send_message(req.to, req.subject, req.body, req.cc_team)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Send failed"))
    return result

@router.post("/reply")
def reply_to_email(
    req: ReplyEmailRequest,
    user: dict = Depends(require_auth)
):
    """Reply to email thread"""
    service = get_email_service(user["user_id"])
    result = service.reply_to_thread(req.thread_id, req.body, req.cc_team)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Reply failed"))
    return result

@router.post("/share-insight")
def share_insight_via_email(
    insight: str = Form(None),
    chart_json: Optional[str] = Form(None),
    user: dict = Depends(require_auth)
):
    """Share an AI insight with team via email"""
    team_members = TeamManager.get_members(user["user_id"])
    
    body = f"Shared Insight from DataInsight Pro:\\n\\n{insight}" if insight else "Shared from DataInsight Pro"
    if chart_json:
        body += "\\n\\n[Chart visualization attached]"
    
    service = get_email_service(user["user_id"])
    result = service.send_message(
        team_members[0] if team_members else "team",
        "DataInsight Pro: Shared Insight",
        body,
        cc_team=True,
        chart_json=chart_json
    )
    return result

@router.post("/share-chart")
def share_chart_to_chat(
    req: EmailShareChartRequest,
    user: dict = Depends(require_auth)
):
    """Share a chart to team chat"""
    service = get_email_service(user["user_id"])
    result = service.share_chart(req.chart_json, req.title)
    return result

# ============== Gmail OAuth Endpoints ==============

@router.get("/auth/gmail/status")
def gmail_status(user: dict = Depends(require_auth)):
    """Check if user has connected Gmail"""
    return {
        "configured": gmail_is_configured(),
        "connected": gmail_is_connected(user["user_id"]),
        "email": gmail_get_user_email(user["user_id"]) if gmail_is_connected(user["user_id"]) else None
    }

@router.get("/auth/gmail/url")
def gmail_auth_url(user: dict = Depends(require_auth)):
    """Get Gmail OAuth URL with user state"""
    if not gmail_is_configured():
        raise HTTPException(status_code=500, detail="Gmail API not configured")
    
    # Include user_id in state
    state = base64.urlsafe_b64encode(user["user_id"].encode()).decode()
    
    from src.gmail_service import get_auth_url
    url = get_auth_url(state=state)
    
    return {"auth_url": url}

@router.get("/auth/gmail/callback")
def gmail_callback(code: str = Query(...), state: str = Query(None)):
    """Handle Gmail OAuth callback"""
    tokens = exchange_code_for_tokens(code)
    if not tokens:
        error_html = """
        <html>
        <head><title>Gmail Connection Failed</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h2 style="color: #ef4444;">❌ Connection Failed</h2>
            <p>Failed to connect Gmail. Please try again.</p>
            <p><a href="javascript:window.close()">Close this window</a></p>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)
    
    # Decode user_id from state and save tokens
    user_id = None
    if state:
        try:
            user_id = base64.urlsafe_b64decode(state).decode()
            store_user_tokens(user_id, tokens)
        except:
            pass
    
    success_html = """
    <html>
    <head><title>Gmail Connected!</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh;">
        <div style="background: white; padding: 40px; border-radius: 16px; max-width: 400px; margin: 0 auto; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
            <h2 style="color: #10b981; margin-bottom: 20px;">✅ Gmail Connected!</h2>
            <p style="color: #6b7280;">Your Gmail account has been connected successfully.</p>
            <p style="color: #6b7280; margin-top: 20px;">You can close this window and return to the app.</p>
            <p style="color: #9ca3af; font-size: 0.85rem; margin-top: 30px;">Click "Check Connection" in the app to verify.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=success_html)

@router.post("/auth/gmail/save-tokens")
def save_gmail_tokens(req: GmailTokensRequest, user: dict = Depends(require_auth)):
    """Save Gmail tokens for user"""
    store_user_tokens(user["user_id"], req.tokens)
    return {"success": True}