"""
Team Chat Service for DataInsight Pro
Combines Gmail API with Supabase for persistent chat
"""
from typing import Optional, Dict, List
from datetime import datetime

from src.database import supabase, SUPABASE_AVAILABLE
from src.gmail_service import (
    send_group_message, get_thread_messages, is_user_connected,
    get_user_email
)


class ChatService:
    """Service for managing team chat groups and messages"""
    
    @staticmethod
    def create_group(owner_id: str, name: str, description: str = None, owner_email: str = None) -> Optional[Dict]:
        """Create a new chat group"""
        if not SUPABASE_AVAILABLE:
            return {"success": False, "error": "Database not available"}
        
        try:
            result = supabase.table("chat_groups").insert({
                "owner_id": owner_id,
                "name": name,
                "description": description
            }).execute()
            
            if result.data:
                group = result.data[0]
                # Add owner as first member if email provided
                if owner_email:
                    ChatService.add_member(group["id"], owner_email, "Owner")
                
                return {
                    "success": True,
                    "group_id": group["id"],
                    "name": group["name"]
                }
        except Exception as e:
            print(f"Create group error: {e}")
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Failed to create group"}
    
    @staticmethod
    def get_user_groups(user_id: str, user_email: str = None) -> List[Dict]:
        """Get all groups user is part of (owned or member)"""
        if not SUPABASE_AVAILABLE:
            return []
        
        try:
            # Get user's email from session if not provided
            if not user_email:
                user_email = get_user_email(user_id)
            
            # Also try to get email from user_sessions table
            if not user_email:
                try:
                    session = supabase.table("user_sessions").select("email").eq("user_id", user_id).limit(1).execute()
                    if session.data:
                        user_email = session.data[0].get("email")
                except:
                    pass
            
            # Get groups owned by user
            owned = supabase.table("chat_groups").select("*").eq("owner_id", user_id).execute()
            groups = owned.data if owned.data else []
            owned_ids = {g["id"] for g in groups}
            
            # Get groups user is member of (by email)
            if user_email:
                member_of = supabase.table("group_members").select("group_id").eq("email", user_email.lower()).execute()
                
                if member_of.data:
                    for m in member_of.data:
                        gid = m["group_id"]
                        if gid not in owned_ids:
                            grp = supabase.table("chat_groups").select("*").eq("id", gid).execute()
                            if grp.data:
                                groups.append(grp.data[0])
            
            # Add member count and last message to each group
            for group in groups:
                members = supabase.table("group_members").select("email", count="exact").eq("group_id", group["id"]).execute()
                group["member_count"] = members.count if members.count else 0
                
                last_msg = supabase.table("chat_messages").select("content,created_at").eq("group_id", group["id"]).order("created_at", desc=True).limit(1).execute()
                if last_msg.data:
                    group["last_message"] = last_msg.data[0]["content"][:50] + "..." if len(last_msg.data[0]["content"]) > 50 else last_msg.data[0]["content"]
                    group["last_activity"] = last_msg.data[0]["created_at"]
                else:
                    group["last_message"] = "No messages yet"
                    group["last_activity"] = group["created_at"]
            
            return sorted(groups, key=lambda x: x.get("last_activity", ""), reverse=True)
        except Exception as e:
            print(f"[Chat] Get groups error: {e}")
            import traceback
            traceback.print_exc()
        
        return []
    
    @staticmethod
    def get_group(group_id: int) -> Optional[Dict]:
        """Get group details"""
        if not SUPABASE_AVAILABLE:
            return None
        
        try:
            result = supabase.table("chat_groups").select("*").eq("id", group_id).execute()
            if result.data:
                group = result.data[0]
                # Get members
                members = supabase.table("group_members").select("*").eq("group_id", group_id).execute()
                group["members"] = members.data if members.data else []
                return group
        except:
            pass
        
        return None
    
    @staticmethod
    def add_member(group_id: int, email: str, name: str = None) -> bool:
        """Add member to group"""
        if not SUPABASE_AVAILABLE:
            return False
        
        try:
            supabase.table("group_members").insert({
                "group_id": group_id,
                "email": email.lower(),
                "name": name
            }).execute()
            return True
        except Exception as e:
            print(f"Add member error: {e}")
            return False
    
    @staticmethod
    def remove_member(group_id: int, email: str) -> bool:
        """Remove member from group"""
        if not SUPABASE_AVAILABLE:
            return False
        
        try:
            supabase.table("group_members").delete().eq("group_id", group_id).eq("email", email.lower()).execute()
            return True
        except:
            return False
    
    @staticmethod
    def get_group_members(group_id: int) -> List[str]:
        """Get list of member emails"""
        if not SUPABASE_AVAILABLE:
            return []
        
        try:
            result = supabase.table("group_members").select("email").eq("group_id", group_id).execute()
            return [m["email"].lower() for m in result.data] if result.data else []
        except Exception as e:
            print(f"[Chat] get_group_members error: {e}")
            return []
    
    @staticmethod
    def send_message(user_id: str, group_id: int, content: str, 
                     sender_email: str, sender_name: str = None,
                     message_type: str = "text", chart_json: str = None,
                     chart_title: str = None) -> Optional[Dict]:
        """
        Send message to group
        - Saves to database
        - Sends email to all group members via Gmail API
        """
        if not SUPABASE_AVAILABLE:
            return {"success": False, "error": "Database not available"}
        
        try:
            # Get group info
            group = ChatService.get_group(group_id)
            if not group:
                return {"success": False, "error": "Group not found"}
            
            # Save message to database first
            msg_data = {
                "group_id": group_id,
                "sender_id": user_id,
                "sender_email": sender_email,
                "sender_name": sender_name or sender_email.split('@')[0],
                "message_type": message_type,
                "content": content
            }
            
            if chart_json:
                msg_data["chart_json"] = chart_json
                msg_data["chart_title"] = chart_title
            
            result = supabase.table("chat_messages").insert(msg_data).execute()
            
            if not result.data:
                return {"success": False, "error": "Failed to save message"}
            
            saved_msg = result.data[0]
            
            # Send email to group members (if Gmail connected)
            gmail_result = None
            gmail_connected = is_user_connected(user_id)
            
            if gmail_connected:
                members = ChatService.get_group_members(group_id)
                
                # Remove sender from recipients
                recipients = [m for m in members if m.lower() != sender_email.lower()]
                
                if recipients:
                    # Build email body
                    email_body = f"{sender_name or sender_email} in {group['name']}:\n\n{content}"
                    
                    if chart_title:
                        email_body += f"\n\n📊 Shared chart: {chart_title}"
                        email_body += f"\n[View in DataInsight Pro]"
                    
                    subject = f"[{group['name']}] New message from {sender_name or sender_email.split('@')[0]}"
                    
                    gmail_result = send_group_message(
                        user_id, recipients, subject, email_body,
                        thread_id=group.get("gmail_thread_id")
                    )
                    
                    # Update group's gmail thread ID if new
                    if gmail_result and gmail_result.get("thread_id"):
                        if not group.get("gmail_thread_id"):
                            supabase.table("chat_groups").update({
                                "gmail_thread_id": gmail_result["thread_id"]
                            }).eq("id", group_id).execute()
                        
                        # Update message with gmail ID
                        supabase.table("chat_messages").update({
                            "gmail_message_id": gmail_result.get("message_id")
                        }).eq("id", saved_msg["id"]).execute()
            
            return {
                "success": True,
                "message_id": saved_msg["id"],
                "gmail_sent": gmail_result is not None,
                "gmail_error": None if gmail_result else ("Gmail not connected" if not gmail_connected else "No recipients"),
                "timestamp": saved_msg["created_at"]
            }
            
        except Exception as e:
            print(f"[Chat] Send message error: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_messages(group_id: int, limit: int = 50, before_id: int = None) -> List[Dict]:
        """Get messages for a group"""
        if not SUPABASE_AVAILABLE:
            return []
        
        try:
            query = supabase.table("chat_messages").select("*").eq("group_id", group_id)
            
            if before_id:
                query = query.lt("id", before_id)
            
            result = query.order("created_at", desc=False).limit(limit).execute()
            
            messages = result.data if result.data else []
            
            # Format messages for display
            formatted = []
            for msg in messages:
                formatted.append({
                    "id": msg["id"],
                    "sender_id": msg["sender_id"],
                    "sender_email": msg["sender_email"],
                    "sender_name": msg.get("sender_name") or msg["sender_email"].split('@')[0],
                    "type": msg.get("message_type", "text"),
                    "content": msg["content"],
                    "chart_json": msg.get("chart_json"),
                    "chart_title": msg.get("chart_title"),
                    "timestamp": msg["created_at"],
                    "is_email_synced": bool(msg.get("gmail_message_id"))
                })
            
            return formatted
        except Exception as e:
            print(f"Get messages error: {e}")
        
        return []
    
    @staticmethod
    def share_chart(user_id: str, group_id: int, chart_json: str, 
                    chart_title: str, sender_email: str, sender_name: str = None) -> Optional[Dict]:
        """Share a chart to a group"""
        return ChatService.send_message(
            user_id=user_id,
            group_id=group_id,
            content=f"📊 Shared chart: {chart_title}",
            sender_email=sender_email,
            sender_name=sender_name,
            message_type="chart",
            chart_json=chart_json,
            chart_title=chart_title
        )
    
    @staticmethod
    def delete_group(group_id: int, owner_id: str) -> bool:
        """Delete a group (owner only)"""
        if not SUPABASE_AVAILABLE:
            return False
        
        try:
            # Verify ownership
            group = supabase.table("chat_groups").select("owner_id").eq("id", group_id).execute()
            if not group.data or group.data[0]["owner_id"] != owner_id:
                return False
            
            # Delete (cascade will handle members and messages)
            supabase.table("chat_groups").delete().eq("id", group_id).execute()
            return True
        except:
            return False


# Convenience function
def get_chat_service():
    return ChatService
