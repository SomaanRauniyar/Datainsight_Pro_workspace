"""
Calendar Routes - Event management and scheduling
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List

from src.calendar_agent import CalendarService, scan_messages_for_events, extract_scheduling_intent
from src.chat_service import ChatService
from ..dependencies import require_auth
from ..models import CreateEventRequest, UpdateEventRequest, AcceptSuggestionRequest

router = APIRouter()

@router.get("/events")
def get_calendar_events(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: dict = Depends(require_auth)
):
    """Get user's calendar events"""
    events = CalendarService.get_user_events(user["user_id"], start_date, end_date)
    return {"events": events}

@router.post("/events")
def create_calendar_event(req: CreateEventRequest, user: dict = Depends(require_auth)):
    """Create a new calendar event"""
    try:
        event = CalendarService.create_event(user["user_id"], {
            "title": req.title,
            "event_type": req.event_type,
            "date": req.date,
            "time": req.time,
            "duration_minutes": req.duration_minutes,
            "participants": req.participants
        })
        
        if not event:
            raise HTTPException(status_code=400, detail="Failed to create event. Make sure calendar tables exist in Supabase.")
        
        return {"success": True, "event": event}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating event: {str(e)}")

@router.put("/events/{event_id}")
def update_calendar_event(event_id: int, req: UpdateEventRequest, user: dict = Depends(require_auth)):
    """Update a calendar event"""
    updates = {k: v for k, v in req.dict().items() if v is not None}
    
    if req.date and req.time:
        updates["start_time"] = f"{req.date}T{req.time}:00"
    elif req.date:
        updates["start_time"] = f"{req.date}T09:00:00"
    
    # Remove date/time from updates as we've converted to start_time
    updates.pop("date", None)
    updates.pop("time", None)
    
    success = CalendarService.update_event(event_id, user["user_id"], updates)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update event")
    
    return {"success": True}

@router.delete("/events/{event_id}")
def delete_calendar_event(event_id: int, user: dict = Depends(require_auth)):
    """Delete a calendar event"""
    success = CalendarService.delete_event(event_id, user["user_id"])
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete event")
    
    return {"success": True}

@router.get("/suggestions")
def get_event_suggestions(user: dict = Depends(require_auth)):
    """Get pending event suggestions"""
    try:
        suggestions = CalendarService.get_pending_suggestions(user["user_id"])
        return {"suggestions": suggestions or []}
    except Exception as e:
        # Return empty array instead of crashing
        print(f"[WARNING] Calendar suggestions error: {e}")
        return {"suggestions": []}

@router.post("/suggestions/{suggestion_id}/accept")
def accept_event_suggestion(
    suggestion_id: int, 
    req: AcceptSuggestionRequest = None,
    user: dict = Depends(require_auth)
):
    """Accept an event suggestion and create calendar event"""
    modifications = req.dict() if req else None
    event = CalendarService.accept_suggestion(suggestion_id, user["user_id"], modifications)
    
    if not event:
        raise HTTPException(status_code=400, detail="Failed to accept suggestion")
    
    return {"success": True, "event": event}

@router.post("/suggestions/{suggestion_id}/dismiss")
def dismiss_event_suggestion(suggestion_id: int, user: dict = Depends(require_auth)):
    """Dismiss an event suggestion"""
    success = CalendarService.dismiss_suggestion(suggestion_id, user["user_id"])
    if not success:
        raise HTTPException(status_code=400, detail="Failed to dismiss suggestion")
    
    return {"success": True}

@router.post("/scan-messages")
def scan_messages_for_scheduling(
    group_id: int = Query(...),
    user: dict = Depends(require_auth)
):
    """Scan recent messages in a group for scheduling intent"""
    # Get recent messages
    messages = ChatService.get_messages(group_id, limit=20)
    
    # Scan for events
    detected_events = scan_messages_for_events(messages)
    
    # Create suggestions for detected events
    suggestions = []
    for event_data in detected_events:
        suggestion = CalendarService.create_suggestion(user["user_id"], event_data)
        if suggestion:
            suggestions.append(suggestion)
    
    return {
        "detected": len(detected_events),
        "suggestions_created": len(suggestions),
        "suggestions": suggestions
    }

@router.post("/analyze-message")
def analyze_message_for_scheduling(
    message: str = Query(...),
    user: dict = Depends(require_auth)
):
    """Analyze a single message for scheduling intent"""
    event_data = extract_scheduling_intent(message)
    
    if event_data:
        return {
            "found": True,
            "event": event_data
        }
    
    return {"found": False}