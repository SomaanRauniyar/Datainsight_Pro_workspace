"""
Team Management Routes - Team creation and member management
"""
from fastapi import APIRouter, HTTPException, Depends

from src.team_manager import TeamManager
from ..dependencies import require_auth
from ..models import TeamMemberRequest

router = APIRouter()

@router.get("/")
def get_team(user: dict = Depends(require_auth)):
    """Get or create user's team"""
    team = TeamManager.get_or_create_team(user["user_id"])
    return team

@router.post("/members")
def add_team_member(req: TeamMemberRequest, user: dict = Depends(require_auth)):
    """Add member to team"""
    result = TeamManager.add_member(user["user_id"], req.email)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.delete("/members/{email}")
def remove_team_member(email: str, user: dict = Depends(require_auth)):
    """Remove member from team"""
    result = TeamManager.remove_member(user["user_id"], email)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result