"""
Tests for Email Service Module (Mock Service)
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_PATH"] = "data/test_datainsight.db"

from src.database import init_db, get_connection, create_user
from src.email_service import MockEmailService, get_email_service
from src.team_manager import TeamManager

@pytest.fixture(autouse=True)
def setup_db():
    """Setup fresh test database"""
    init_db()
    yield
    with get_connection() as conn:
        conn.execute("DELETE FROM email_messages")
        conn.execute("DELETE FROM email_threads")
        conn.execute("DELETE FROM team_members")
        conn.execute("DELETE FROM teams")
        conn.execute("DELETE FROM users")
        conn.commit()

@pytest.fixture
def test_user():
    """Create a test user"""
    user_id = create_user("emailtest@example.com", "password123", "Email Tester")
    return user_id

class TestMockEmailService:
    def test_is_connected(self, test_user):
        service = MockEmailService(test_user)
        assert service.is_connected() == True
    
    def test_get_threads(self, test_user):
        service = MockEmailService(test_user)
        threads = service.get_threads()
        
        # Should have at least the sample thread
        assert isinstance(threads, list)
    
    def test_send_message(self, test_user):
        service = MockEmailService(test_user)
        
        result = service.send_message(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test body content",
            cc_team=False
        )
        
        assert result["success"] == True
        assert "message_id" in result
    
    def test_send_message_with_team_cc(self, test_user):
        # Add team members first
        TeamManager.get_or_create_team(test_user)
        TeamManager.add_member(test_user, "team1@example.com")
        TeamManager.add_member(test_user, "team2@example.com")
        
        service = MockEmailService(test_user)
        result = service.send_message(
            to="recipient@example.com",
            subject="Team Update",
            body="Important update",
            cc_team=True
        )
        
        assert result["success"] == True
        assert len(result["cc_recipients"]) == 2
        assert "team1@example.com" in result["cc_recipients"]
    
    def test_reply_to_thread(self, test_user):
        service = MockEmailService(test_user)
        
        # Get existing threads
        threads = service.get_threads()
        if threads:
            thread_id = threads[0]["id"]
            
            result = service.reply_to_thread(
                thread_id=thread_id,
                body="This is my reply",
                cc_team=False
            )
            
            assert result["success"] == True
    
    def test_get_thread_messages(self, test_user):
        service = MockEmailService(test_user)
        
        # Send a message first
        service.send_message("test@example.com", "Test", "Body")
        
        threads = service.get_threads()
        if threads:
            messages = service.get_thread_messages(threads[0]["id"])
            assert isinstance(messages, list)

class TestGetEmailService:
    def test_returns_mock_service(self, test_user):
        # Without Gmail credentials, should return mock service
        service = get_email_service(test_user)
        assert isinstance(service, MockEmailService)

class TestEmailServiceIntegration:
    def test_full_conversation_flow(self, test_user):
        service = MockEmailService(test_user)
        
        # Send initial message
        send_result = service.send_message(
            to="colleague@example.com",
            subject="Project Update",
            body="Here's the latest on the project..."
        )
        assert send_result["success"] == True
        
        # Get threads
        threads = service.get_threads()
        assert len(threads) > 0
        
        # Find our thread
        project_thread = next(
            (t for t in threads if "Project Update" in t.get("subject", "")),
            None
        )
        
        if project_thread:
            # Reply to thread
            reply_result = service.reply_to_thread(
                thread_id=project_thread["id"],
                body="Thanks for the update!"
            )
            assert reply_result["success"] == True
            
            # Get messages in thread
            messages = service.get_thread_messages(project_thread["id"])
            assert len(messages) >= 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
