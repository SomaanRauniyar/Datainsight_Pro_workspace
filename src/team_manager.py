"""
Team Management module for DataInsight Pro
Handles team creation, member management, and group operations
"""
from typing import List, Dict, Optional
from src.database import (
    create_team, get_user_team, add_team_member,
    remove_team_member, get_team_members, get_user_by_id
)

class TeamManager:
    """Manages team operations for collaboration features"""
    
    @staticmethod
    def get_or_create_team(user_id: int, team_name: str = "My Team") -> Dict:
        """Get existing team or create new one for user"""
        team = get_user_team(user_id)
        if team:
            members = get_team_members(team['id'])
            return {
                "team_id": team['id'],
                "name": team['name'],
                "members": members,
                "is_new": False
            }
        
        team_id = create_team(user_id, team_name)
        return {
            "team_id": team_id,
            "name": team_name,
            "members": [],
            "is_new": True
        }
    
    @staticmethod
    def add_member(user_id: int, member_email: str) -> Dict:
        """Add a team member by email"""
        team = get_user_team(user_id)
        if not team:
            return {"success": False, "error": "No team found. Create a team first."}
        
        if not member_email or '@' not in member_email:
            return {"success": False, "error": "Invalid email address"}
        
        # Check if already a member
        members = get_team_members(team['id'])
        if member_email.lower() in [m.lower() for m in members]:
            return {"success": False, "error": "Member already in team"}
        
        success = add_team_member(team['id'], member_email)
        if success:
            return {
                "success": True,
                "message": f"Added {member_email} to team",
                "members": get_team_members(team['id'])
            }
        return {"success": False, "error": "Failed to add member"}
    
    @staticmethod
    def remove_member(user_id: int, member_email: str) -> Dict:
        """Remove a team member"""
        team = get_user_team(user_id)
        if not team:
            return {"success": False, "error": "No team found"}
        
        success = remove_team_member(team['id'], member_email)
        if success:
            return {
                "success": True,
                "message": f"Removed {member_email} from team",
                "members": get_team_members(team['id'])
            }
        return {"success": False, "error": "Member not found in team"}
    
    @staticmethod
    def get_members(user_id: int) -> List[str]:
        """Get all team members for a user"""
        team = get_user_team(user_id)
        if team:
            return get_team_members(team['id'])
        return []
    
    @staticmethod
    def get_team_info(user_id: int) -> Optional[Dict]:
        """Get full team information"""
        team = get_user_team(user_id)
        if team:
            user = get_user_by_id(user_id)
            members = get_team_members(team['id'])
            return {
                "team_id": team['id'],
                "name": team['name'],
                "owner_email": user['email'] if user else None,
                "members": members,
                "member_count": len(members)
            }
        return None
