"""
Tests for Team Management Module
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, get_connection, create_user
from src.team_manager import TeamManager

os.environ["DATABASE_PATH"] = "data/test_datainsight.db"

@pytest.fixture(autouse=True)
def setup_db():
    """Setup fresh test database"""
    init_db()
    yield
    with get_connection() as conn:
        conn.execute("DELETE FROM team_members")
        conn.execute("DELETE FROM teams")
        conn.execute("DELETE FROM users")
        conn.commit()

@pytest.fixture
def test_user():
    """Create a test user"""
    user_id = create_user("teamtest@example.com", "password123", "Team Tester")
    return user_id

class TestTeamManager:
    def test_create_team(self, test_user):
        result = TeamManager.get_or_create_team(test_user, "Test Team")
        assert result["team_id"] is not None
        assert result["name"] == "Test Team"
        assert result["is_new"] == True
        assert result["members"] == []
    
    def test_get_existing_team(self, test_user):
        # Create team
        TeamManager.get_or_create_team(test_user, "Existing Team")
        
        # Get same team
        result = TeamManager.get_or_create_team(test_user)
        assert result["is_new"] == False
        assert result["name"] == "Existing Team"
    
    def test_add_member(self, test_user):
        TeamManager.get_or_create_team(test_user)
        
        result = TeamManager.add_member(test_user, "member1@example.com")
        assert result["success"] == True
        assert "member1@example.com" in result["members"]
    
    def test_add_duplicate_member(self, test_user):
        TeamManager.get_or_create_team(test_user)
        TeamManager.add_member(test_user, "dup@example.com")
        
        result = TeamManager.add_member(test_user, "dup@example.com")
        assert result["success"] == False
        assert "already" in result["error"].lower()
    
    def test_add_invalid_email(self, test_user):
        TeamManager.get_or_create_team(test_user)
        
        result = TeamManager.add_member(test_user, "invalid-email")
        assert result["success"] == False
    
    def test_remove_member(self, test_user):
        TeamManager.get_or_create_team(test_user)
        TeamManager.add_member(test_user, "remove@example.com")
        
        result = TeamManager.remove_member(test_user, "remove@example.com")
        assert result["success"] == True
        assert "remove@example.com" not in result["members"]
    
    def test_remove_nonexistent_member(self, test_user):
        TeamManager.get_or_create_team(test_user)
        
        result = TeamManager.remove_member(test_user, "nonexistent@example.com")
        assert result["success"] == False
    
    def test_get_members(self, test_user):
        TeamManager.get_or_create_team(test_user)
        TeamManager.add_member(test_user, "m1@example.com")
        TeamManager.add_member(test_user, "m2@example.com")
        
        members = TeamManager.get_members(test_user)
        assert len(members) == 2
        assert "m1@example.com" in members
        assert "m2@example.com" in members
    
    def test_get_team_info(self, test_user):
        TeamManager.get_or_create_team(test_user, "Info Team")
        TeamManager.add_member(test_user, "info@example.com")
        
        info = TeamManager.get_team_info(test_user)
        assert info is not None
        assert info["name"] == "Info Team"
        assert info["member_count"] == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
