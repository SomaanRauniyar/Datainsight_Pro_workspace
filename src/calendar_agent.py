"""
Agentic Calendar System
Scans messages for scheduling intent and suggests calendar events
"""
import os
import re
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from groq import Groq

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def extract_scheduling_intent(message: str, context: str = "") -> Optional[Dict]:
    """
    Use LLM to extract scheduling intent from a message
    Returns event details if scheduling intent found, None otherwise
    """
    if not client:
        return None
    
    today = datetime.now()
    
    prompt = f"""Analyze this chat message for scheduling intent. 
Today's date is {today.strftime('%A, %B %d, %Y')}.

Message: "{message}"
{f'Context (surrounding messages): {context}' if context else ''}

If this message contains a scheduling request (meeting, call, appointment, deadline, etc.), extract:
1. event_type: "meeting", "call", "deadline", "reminder", "appointment", or "other"
2. title: A DESCRIPTIVE title for the event based on the PURPOSE mentioned in the message or context. 
   - Look for keywords like: discuss, review, sync, standup, planning, demo, interview, presentation, etc.
   - Examples: "Project Review Meeting", "Sales Call with Client", "Q4 Planning Session", "Team Standup"
   - If no clear purpose is mentioned, use the sender's name + event type (e.g., "Meeting with John")
   - ONLY use generic "Meeting" as absolute last resort
3. date: The date mentioned (convert relative dates like "tomorrow", "Monday" to actual dates in YYYY-MM-DD format)
4. time: Time in HH:MM format (24-hour), or null if not specified
5. duration_minutes: Estimated duration in minutes (default 60 for meetings)
6. participants: List of people mentioned
7. confidence: Your confidence level 0-100

IMPORTANT: The title should be descriptive and meaningful, not just "Meeting" or "Call".

If NO scheduling intent is found, return {{"found": false}}

Return ONLY valid JSON, no explanation."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up response
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        result = json.loads(result_text)
        
        if result.get("found") == False:
            return None
        
        # Validate and return
        if result.get("date") and result.get("confidence", 0) >= 50:
            # Ensure title is not too generic
            title = result.get("title", "Meeting")
            if title.lower() in ["meeting", "call", "event", "appointment"]:
                # Try to make it more descriptive from the message
                title = _extract_better_title(message, context, result.get("event_type", "meeting"))
            
            return {
                "event_type": result.get("event_type", "meeting"),
                "title": title,
                "date": result.get("date"),
                "time": result.get("time"),
                "duration_minutes": result.get("duration_minutes", 60),
                "participants": result.get("participants", []),
                "confidence": result.get("confidence", 50),
                "source_message": message
            }
        
        return None
        
    except Exception as e:
        print(f"[Calendar Agent] Error extracting intent: {e}")
        return None


def _extract_better_title(message: str, context: str, event_type: str) -> str:
    """Extract a more descriptive title from message content"""
    combined = f"{context} {message}".lower()
    
    # Common meeting purposes
    purpose_keywords = {
        "standup": "Daily Standup",
        "stand-up": "Daily Standup",
        "sync": "Team Sync",
        "review": "Review Meeting",
        "planning": "Planning Session",
        "sprint": "Sprint Planning",
        "demo": "Demo Session",
        "presentation": "Presentation",
        "interview": "Interview",
        "onboarding": "Onboarding Session",
        "training": "Training Session",
        "workshop": "Workshop",
        "brainstorm": "Brainstorming Session",
        "kickoff": "Project Kickoff",
        "kick-off": "Project Kickoff",
        "retro": "Retrospective",
        "retrospective": "Retrospective",
        "1:1": "1:1 Meeting",
        "one on one": "1:1 Meeting",
        "catch up": "Catch-up Call",
        "catchup": "Catch-up Call",
        "discuss": "Discussion",
        "budget": "Budget Review",
        "sales": "Sales Meeting",
        "client": "Client Meeting",
        "customer": "Customer Call",
        "project": "Project Meeting",
        "status": "Status Update",
        "update": "Status Update",
        "weekly": "Weekly Meeting",
        "monthly": "Monthly Review",
        "quarterly": "Quarterly Review",
    }
    
    for keyword, title in purpose_keywords.items():
        if keyword in combined:
            return title
    
    # If still no match, capitalize the event type
    return event_type.replace("_", " ").title()


def scan_messages_for_events(messages: List[Dict]) -> List[Dict]:
    """
    Scan a list of messages and extract all scheduling intents
    Passes surrounding context to help extract better event titles
    """
    events = []
    recent_messages = messages[-15:]  # Scan last 15 messages
    
    for idx, msg in enumerate(recent_messages):
        content = msg.get("content", "")
        
        # Quick pre-filter to avoid unnecessary LLM calls
        scheduling_keywords = [
            "meet", "meeting", "call", "schedule", "appointment",
            "tomorrow", "monday", "tuesday", "wednesday", "thursday", 
            "friday", "saturday", "sunday", "am", "pm", "o'clock",
            "deadline", "due", "remind", "calendar", "sync", "standup",
            "review", "demo", "presentation", "interview", "discuss"
        ]
        
        if any(kw in content.lower() for kw in scheduling_keywords):
            # Build context from surrounding messages (2 before, 2 after)
            context_parts = []
            for i in range(max(0, idx - 2), min(len(recent_messages), idx + 3)):
                if i != idx:
                    ctx_msg = recent_messages[i]
                    sender = ctx_msg.get('sender_name') or ctx_msg.get('sender_email', 'User')
                    context_parts.append(f"{sender}: {ctx_msg.get('content', '')}")
            
            context = "\n".join(context_parts)
            
            event = extract_scheduling_intent(content, context)
            if event:
                event["message_id"] = msg.get("id")
                event["sender"] = msg.get("sender_name") or msg.get("sender_email")
                events.append(event)
    
    return events


class CalendarService:
    """Service for managing calendar events"""
    
    @staticmethod
    def create_event(user_id: str, event_data: Dict) -> Optional[Dict]:
        """Create a new calendar event"""
        from src.database import supabase, SUPABASE_AVAILABLE
        
        if not SUPABASE_AVAILABLE:
            print("[Calendar] Supabase not available")
            return None
        
        try:
            # Parse date and time
            event_date = event_data.get("date")
            event_time = event_data.get("time") or "09:00"
            
            # Handle time format - ensure it's HH:MM
            if event_time and ":" in event_time:
                time_parts = event_time.split(":")
                event_time = f"{time_parts[0].zfill(2)}:{time_parts[1].zfill(2)}"
            
            start_datetime = f"{event_date}T{event_time}:00"
            
            # Calculate end time
            duration = event_data.get("duration_minutes", 60)
            
            insert_data = {
                "user_id": user_id,
                "title": event_data.get("title"),
                "event_type": event_data.get("event_type", "meeting"),
                "start_time": start_datetime,
                "duration_minutes": duration,
                "participants": json.dumps(event_data.get("participants", [])),
                "status": "confirmed"
            }
            
            # Only add source_message_id if it exists and is valid
            if event_data.get("message_id"):
                insert_data["source_message_id"] = event_data.get("message_id")
            
            print(f"[Calendar] Creating event: {insert_data}")
            
            result = supabase.table("calendar_events").insert(insert_data).execute()
            
            print(f"[Calendar] Create result: {result}")
            
            if result.data:
                return result.data[0]
        except Exception as e:
            print(f"[Calendar] Create event error: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    @staticmethod
    def get_user_events(user_id: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get user's calendar events"""
        from src.database import supabase, SUPABASE_AVAILABLE
        
        if not SUPABASE_AVAILABLE:
            return []
        
        try:
            query = supabase.table("calendar_events").select("*").eq("user_id", user_id)
            
            if start_date:
                query = query.gte("start_time", start_date)
            if end_date:
                query = query.lte("start_time", end_date)
            
            result = query.order("start_time").execute()
            
            events = []
            for event in result.data or []:
                event["participants"] = json.loads(event.get("participants", "[]"))
                events.append(event)
            
            return events
        except Exception as e:
            print(f"[Calendar] Get events error: {e}")
        
        return []
    
    @staticmethod
    def update_event(event_id: int, user_id: str, updates: Dict) -> bool:
        """Update a calendar event"""
        from src.database import supabase, SUPABASE_AVAILABLE
        
        if not SUPABASE_AVAILABLE:
            return False
        
        try:
            # Verify ownership
            existing = supabase.table("calendar_events").select("user_id").eq("id", event_id).execute()
            if not existing.data or existing.data[0]["user_id"] != user_id:
                return False
            
            if "participants" in updates:
                updates["participants"] = json.dumps(updates["participants"])
            
            supabase.table("calendar_events").update(updates).eq("id", event_id).execute()
            return True
        except Exception as e:
            print(f"[Calendar] Update event error: {e}")
        
        return False
    
    @staticmethod
    def delete_event(event_id: int, user_id: str) -> bool:
        """Delete a calendar event"""
        from src.database import supabase, SUPABASE_AVAILABLE
        
        if not SUPABASE_AVAILABLE:
            return False
        
        try:
            # Verify ownership
            existing = supabase.table("calendar_events").select("user_id").eq("id", event_id).execute()
            if not existing.data or existing.data[0]["user_id"] != user_id:
                return False
            
            supabase.table("calendar_events").delete().eq("id", event_id).execute()
            return True
        except:
            return False
    
    @staticmethod
    def get_pending_suggestions(user_id: str) -> List[Dict]:
        """Get pending event suggestions for user"""
        from src.database import supabase, SUPABASE_AVAILABLE
        
        if not SUPABASE_AVAILABLE:
            print("[Calendar] Supabase not available for get_pending_suggestions")
            return []
        
        try:
            print(f"[Calendar] Fetching suggestions for user_id: {user_id}")
            result = supabase.table("event_suggestions").select("*").eq("user_id", user_id).eq("status", "pending").execute()
            print(f"[Calendar] Found {len(result.data or [])} pending suggestions")
            
            # Parse participants JSON for each suggestion
            suggestions = []
            for s in result.data or []:
                if s.get("participants"):
                    try:
                        s["participants"] = json.loads(s["participants"])
                    except:
                        s["participants"] = []
                suggestions.append(s)
            
            return suggestions
        except Exception as e:
            print(f"[Calendar] Error fetching suggestions: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def create_suggestion(user_id: str, event_data: Dict) -> Optional[Dict]:
        """Create a pending event suggestion"""
        from src.database import supabase, SUPABASE_AVAILABLE
        
        if not SUPABASE_AVAILABLE:
            print("[Calendar] Supabase not available for suggestions")
            return None
        
        try:
            # Ensure date is in correct format
            suggested_date = event_data.get("date")
            suggested_time = event_data.get("time")
            
            # Handle time format - ensure it's HH:MM:SS for TIME column
            if suggested_time:
                if len(suggested_time) == 5:  # HH:MM format
                    suggested_time = f"{suggested_time}:00"
            
            insert_data = {
                "user_id": str(user_id),  # Ensure string
                "title": event_data.get("title", "Untitled Event"),
                "event_type": event_data.get("event_type", "meeting"),
                "suggested_date": suggested_date,
                "suggested_time": suggested_time,
                "duration_minutes": event_data.get("duration_minutes", 60),
                "participants": json.dumps(event_data.get("participants", [])),
                "source_message": event_data.get("source_message", "")[:500] if event_data.get("source_message") else None,
                "confidence": event_data.get("confidence", 50),
                "status": "pending"
            }
            
            print(f"[Calendar] Creating suggestion with data: {insert_data}")
            
            result = supabase.table("event_suggestions").insert(insert_data).execute()
            
            print(f"[Calendar] Insert result: {result.data}")
            
            if result.data:
                return result.data[0]
            else:
                print(f"[Calendar] No data returned from insert")
                return None
        except Exception as e:
            print(f"[Calendar] Create suggestion error: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    @staticmethod
    def accept_suggestion(suggestion_id: int, user_id: str, modifications: Dict = None) -> Optional[Dict]:
        """Accept a suggestion and create calendar event"""
        from src.database import supabase, SUPABASE_AVAILABLE
        
        if not SUPABASE_AVAILABLE:
            return None
        
        try:
            # Get suggestion
            result = supabase.table("event_suggestions").select("*").eq("id", suggestion_id).eq("user_id", user_id).execute()
            if not result.data:
                return None
            
            suggestion = result.data[0]
            
            # Apply modifications
            event_data = {
                "title": modifications.get("title") if modifications else suggestion["title"],
                "event_type": suggestion["event_type"],
                "date": modifications.get("date") if modifications else suggestion["suggested_date"],
                "time": modifications.get("time") if modifications else suggestion["suggested_time"],
                "duration_minutes": modifications.get("duration_minutes") if modifications else suggestion["duration_minutes"],
                "participants": json.loads(suggestion.get("participants", "[]"))
            }
            
            # Create event
            event = CalendarService.create_event(user_id, event_data)
            
            if event:
                # Mark suggestion as accepted
                supabase.table("event_suggestions").update({"status": "accepted"}).eq("id", suggestion_id).execute()
                return event
        except Exception as e:
            print(f"[Calendar] Accept suggestion error: {e}")
        
        return None
    
    @staticmethod
    def dismiss_suggestion(suggestion_id: int, user_id: str) -> bool:
        """Dismiss a suggestion"""
        from src.database import supabase, SUPABASE_AVAILABLE
        
        if not SUPABASE_AVAILABLE:
            return False
        
        try:
            supabase.table("event_suggestions").update({"status": "dismissed"}).eq("id", suggestion_id).eq("user_id", user_id).execute()
            return True
        except:
            return False
