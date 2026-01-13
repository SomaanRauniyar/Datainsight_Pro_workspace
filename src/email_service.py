"""
Email/Communication Service for DataInsight Pro (Postman Module)
In-memory team messaging for development
"""
import os
from datetime import datetime
from typing import Dict, List, Optional

from src.database import (
    get_email_threads, create_email_thread, add_email_message,
    get_thread_messages, get_or_create_contact_thread, add_shared_chart
)
from src.team_manager import TeamManager


class MockEmailService:
    """Mock email service using in-memory storage"""
    
    def __init__(self, user_id: str):
        self.user_id = str(user_id)
        self._init_sample_thread()
    
    def _init_sample_thread(self):
        """Create a sample thread if user has none"""
        threads = get_email_threads(self.user_id, limit=1)
        if not threads:
            thread_id = create_email_thread(
                self.user_id, 
                "Welcome to DataInsight Pro Team Chat"
            )
            if thread_id:
                add_email_message(
                    thread_id,
                    sender="DataInsight Pro",
                    recipients="you",
                    body="Welcome to team collaboration! Share insights and communicate with your team here.",
                    is_from_user=False
                )
    
    def is_connected(self) -> bool:
        return True
    
    def get_threads(self, max_results: int = 20) -> List[Dict]:
        """Get email threads"""
        threads = get_email_threads(self.user_id, max_results)
        return [
            {
                'id': str(t['id']),
                'subject': t.get('subject', 'No Subject'),
                'from': 'Team',
                'date': t.get('last_updated', ''),
                'snippet': 'Click to view conversation...',
                'message_count': t.get('message_count', 1),
                'contact': t.get('contact', '')
            }
            for t in threads
        ]
    
    def get_thread_messages(self, thread_id: str) -> List[Dict]:
        """Get messages in a thread"""
        messages = get_thread_messages(int(thread_id))
        return [
            {
                'id': str(m['id']),
                'from': m.get('sender', 'Unknown'),
                'to': m.get('recipients', ''),
                'date': m.get('sent_at', ''),
                'body': m.get('body', ''),
                'is_from_user': m.get('is_from_user', False),
                'chart_json': m.get('chart_json')
            }
            for m in messages
        ]
    
    def send_message(self, to: str, subject: str, body: str, cc_team: bool = True, chart_json: str = None) -> Dict:
        """Send a message - adds to existing thread with contact or creates new one"""
        cc_list = TeamManager.get_members(self.user_id) if cc_team else []
        recipients = to + (f", {', '.join(cc_list)}" if cc_list else "")
        
        # Get or create thread for this contact (keeps messages in same thread)
        thread_id = get_or_create_contact_thread(self.user_id, to, subject)
        if not thread_id:
            return {"success": False, "error": "Failed to get/create thread"}
        
        # Add message to thread
        msg_id = add_email_message(
            thread_id,
            sender="You",
            recipients=recipients,
            body=body,
            is_from_user=True,
            chart_json=chart_json
        )
        
        if msg_id:
            return {
                "success": True,
                "message_id": str(msg_id),
                "thread_id": str(thread_id),
                "cc_recipients": cc_list
            }
        return {"success": False, "error": "Failed to send message"}
    
    def reply_to_thread(self, thread_id: str, body: str, cc_team: bool = True, chart_json: str = None) -> Dict:
        """Reply to an existing thread"""
        cc_list = TeamManager.get_members(self.user_id) if cc_team else []
        recipients = "Team" + (f", {', '.join(cc_list)}" if cc_list else "")
        
        msg_id = add_email_message(
            int(thread_id),
            sender="You",
            recipients=recipients,
            body=body,
            is_from_user=True,
            chart_json=chart_json
        )
        
        if msg_id:
            return {
                "success": True,
                "message_id": str(msg_id),
                "cc_recipients": cc_list
            }
        return {"success": False, "error": "Failed to send reply"}
    
    def share_chart(self, chart_json: str, title: str = "Shared Chart") -> Dict:
        """Share a chart to the team chat"""
        # Get team members
        cc_list = TeamManager.get_members(self.user_id)
        
        # Get or create a "Team Charts" thread
        thread_id = get_or_create_contact_thread(self.user_id, "team", "Shared Charts & Insights")
        if not thread_id:
            return {"success": False, "error": "Failed to create chart thread"}
        
        # Add chart message
        msg_id = add_email_message(
            thread_id,
            sender="You",
            recipients=f"Team ({', '.join(cc_list)})" if cc_list else "Team",
            body=f"📊 {title}",
            is_from_user=True,
            chart_json=chart_json
        )
        
        if msg_id:
            return {
                "success": True,
                "message_id": str(msg_id),
                "thread_id": str(thread_id)
            }
        return {"success": False, "error": "Failed to share chart"}


def get_email_service(user_id: str):
    """Get email service for user"""
    return MockEmailService(user_id)
