"""
Chat Routes - Team chat groups and messaging
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional

from src.chat_service import ChatService
from ..dependencies import require_auth
from ..models import CreateGroupRequest, AddMemberRequest, SendMessageRequest, ShareChartRequest

router = APIRouter()

@router.post("/groups")
def create_chat_group(req: CreateGroupRequest, user: dict = Depends(require_auth)):
    """Create a new chat group"""
    result = ChatService.create_group(user["user_id"], req.name, req.description, user.get("email"))
    if not result or not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create group"))
    return result

@router.get("/groups")
def get_chat_groups(user: dict = Depends(require_auth)):
    """Get user's chat groups"""
    groups = ChatService.get_user_groups(user["user_id"], user.get("email"))
    return {"groups": groups}

@router.get("/groups/{group_id}")
def get_chat_group(group_id: int, user: dict = Depends(require_auth)):
    """Get chat group details"""
    group = ChatService.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group

@router.delete("/groups/{group_id}")
def delete_chat_group(group_id: int, user: dict = Depends(require_auth)):
    """Delete a chat group (owner only)"""
    success = ChatService.delete_group(group_id, user["user_id"])
    if not success:
        raise HTTPException(status_code=403, detail="Cannot delete group")
    return {"success": True}

@router.post("/groups/{group_id}/members")
def add_group_member(group_id: int, req: AddMemberRequest, user: dict = Depends(require_auth)):
    """Add member to chat group"""
    success = ChatService.add_member(group_id, req.email, req.name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add member")
    return {"success": True}

@router.delete("/groups/{group_id}/members/{email}")
def remove_group_member(group_id: int, email: str, user: dict = Depends(require_auth)):
    """Remove member from chat group"""
    success = ChatService.remove_member(group_id, email)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove member")
    return {"success": True}

@router.post("/groups/{group_id}/messages")
def send_chat_message(group_id: int, req: SendMessageRequest, user: dict = Depends(require_auth)):
    """Send message to chat group"""
    result = ChatService.send_message(
        user_id=user["user_id"],
        group_id=group_id,
        content=req.content,
        sender_email=user["email"],
        sender_name=user.get("name"),
        message_type=req.message_type,
        chart_json=req.chart_json,
        chart_title=req.chart_title
    )
    
    if not result or not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send message"))
    return result

@router.get("/groups/{group_id}/messages")
def get_chat_messages(
    group_id: int, 
    limit: int = Query(50),
    before_id: Optional[int] = Query(None),
    user: dict = Depends(require_auth)
):
    """Get messages for a chat group"""
    messages = ChatService.get_messages(group_id, limit, before_id)
    return {"messages": messages}

@router.post("/share-chart")
def share_chart_to_group(req: ShareChartRequest, user: dict = Depends(require_auth)):
    """Share a chart to a chat group"""
    result = ChatService.share_chart(
        user_id=user["user_id"],
        group_id=req.group_id,
        chart_json=req.chart_json,
        chart_title=req.chart_title,
        sender_email=user["email"],
        sender_name=user.get("name")
    )
    
    if not result or not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to share chart"))
    return result