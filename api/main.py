"""
DataInsight Pro - Main FastAPI Application
Clean, modular entry point with middleware and route registration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from src.config import PINECONE_API_KEY, PINECONE_INDEX, EMBED_DIM
from src.vector_manager import VectorDBManager
from src.security import get_security_headers, check_rate_limit

# Import route modules
from .routes import (
    auth_routes,
    upload_routes,
    query_routes,
    visualization_routes,
    team_routes,
    briefing_routes,
    email_routes,
    admin_routes,
    calendar_routes,
    chat_routes,
    user_routes
)

# Validate required environment variables
if not PINECONE_API_KEY or not PINECONE_INDEX:
    raise ValueError("Missing required Pinecone configuration")

# Initialize FastAPI app
app = FastAPI(
    title="DataInsight Pro API",
    version="2.0.0",
    description="AI-Powered Business Analytics Platform with Team Collaboration",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize global vector database
vector_db = VectorDBManager(
    api_key=PINECONE_API_KEY, 
    index_name=PINECONE_INDEX, 
    dimension=EMBED_DIM
)

# Store in app state for access in routes
app.state.vector_db = vector_db
app.state.data_cache = {}  # In-memory DataFrame cache
app.state.upload_jobs = {}  # Background job tracking

# ============== Middleware Configuration ==============

# CORS configuration - allow all origins for now to fix deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    for header, value in get_security_headers().items():
        response.headers[header] = value
    
    return response

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting per IP address"""
    client_ip = request.client.host if request.client else "unknown"
    
    if not check_rate_limit(f"ip:{client_ip}", max_requests=100, window_seconds=60):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."}
        )
    
    return await call_next(request)

# ============== Route Registration ==============

# Health and status endpoints
@app.get("/")
def root():
    """API root endpoint"""
    return {
        "status": "ok", 
        "message": "DataInsight Pro API v2.0",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}

# Register all route modules
app.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
app.include_router(upload_routes.router, prefix="/upload", tags=["File Upload"])
app.include_router(query_routes.router, prefix="/query", tags=["RAG Queries"])
app.include_router(visualization_routes.router, prefix="/visualize", tags=["Visualizations"])
app.include_router(team_routes.router, prefix="/team", tags=["Team Management"])
app.include_router(briefing_routes.router, prefix="/briefing", tags=["Smart Briefings"])
app.include_router(email_routes.router, prefix="/email", tags=["Email Integration"])
app.include_router(chat_routes.router, prefix="/chat", tags=["Team Chat"])
app.include_router(calendar_routes.router, prefix="/calendar", tags=["Calendar"])
app.include_router(user_routes.router, prefix="/user", tags=["User Management"])
app.include_router(admin_routes.router, prefix="/admin", tags=["Administration"])

# Public endpoints (no prefix)
from src.llm import get_available_models

@app.get("/models")
def list_available_models():
    """Get list of available LLM models (public endpoint)"""
    return {"models": get_available_models()}

# Legacy endpoints for backward compatibility
app.include_router(query_routes.legacy_router, tags=["Legacy"])
app.include_router(visualization_routes.legacy_router, tags=["Legacy"])

# ============== Gmail OAuth Endpoints (at /auth/gmail/*) ==============
from fastapi import Query
from fastapi.responses import HTMLResponse
import base64
from src.gmail_service import (
    get_auth_url as gmail_get_auth_url, exchange_code_for_tokens,
    store_user_tokens, is_user_connected as gmail_is_connected,
    get_user_email as gmail_get_user_email, is_configured as gmail_is_configured
)
from .routes.auth_routes import router as auth_router
from .dependencies import require_auth

@app.get("/auth/gmail/status")
def gmail_status(user: dict = Depends(require_auth)):
    """Check if user has connected Gmail"""
    return {
        "configured": gmail_is_configured(),
        "connected": gmail_is_connected(user["user_id"]),
        "email": gmail_get_user_email(user["user_id"]) if gmail_is_connected(user["user_id"]) else None
    }

@app.get("/auth/gmail/url")
def gmail_auth_url(user: dict = Depends(require_auth)):
    """Get Gmail OAuth URL with user state"""
    if not gmail_is_configured():
        raise HTTPException(status_code=500, detail="Gmail API not configured. Please add GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET to your .env file.")
    
    # Include user_id in state
    state = base64.urlsafe_b64encode(user["user_id"].encode()).decode()
    url = gmail_get_auth_url(state=state)
    
    if not url:
        raise HTTPException(status_code=500, detail="Failed to generate Gmail auth URL")
    
    return {"auth_url": url}

@app.get("/auth/gmail/callback")
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
            <p style="color: #9ca3af; font-size: 0.85rem; margin-top: 30px;">Click the refresh button to verify connection.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=success_html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )