"""
Briefing Routes - Executive summaries and meeting preparation
"""
from fastapi import APIRouter, Form, Query, HTTPException, Depends
from typing import Optional

from src.briefing_system import BriefingSystem
from ..dependencies import require_auth, get_data_cache
from ..models import MeetingPrepRequest

router = APIRouter()

@router.post("/executive-summary")
def generate_executive_summary(
    file_id: str = Form(...),
    user: dict = Depends(require_auth),
    data_cache: dict = Depends(get_data_cache)
):
    """Generate executive summary for uploaded file"""
    df = data_cache.get((str(user["user_id"]), file_id))
    if df is None:
        raise HTTPException(status_code=404, detail="File not found in cache")
    
    content = df.head(50).to_string()
    result = BriefingSystem.generate_executive_summary(content, user["user_id"])
    return result

@router.post("/meeting-prep")
def generate_meeting_prep(
    req: MeetingPrepRequest,
    user: dict = Depends(require_auth)
):
    """Generate meeting preparation talking points"""
    result = BriefingSystem.generate_meeting_prep(req.context, req.insights, user["user_id"])
    return result

@router.get("/history")
def get_briefing_history(
    briefing_type: Optional[str] = Query(None),
    user: dict = Depends(require_auth)
):
    """Get user's briefing history"""
    briefings = BriefingSystem.get_recent_briefings(user["user_id"], briefing_type, limit=20)
    return {"briefings": briefings}

@router.delete("/{briefing_id}")
def delete_briefing(
    briefing_id: int,
    user: dict = Depends(require_auth)
):
    """Delete a briefing"""
    success = BriefingSystem.delete_briefing(briefing_id, user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Briefing not found or cannot be deleted")
    return {"success": True}