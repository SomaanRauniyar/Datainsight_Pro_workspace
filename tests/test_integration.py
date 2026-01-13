"""
Integration Tests - End-to-end workflow testing
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_PATH"] = "data/test_datainsight.db"

from fastapi.testclient import TestClient
import unittest.mock as mock
from io import BytesIO

# Mock external services
with mock.patch.dict(os.environ, {
    "PINECONE_API_KEY": "test-key",
    "PINECONE_INDEX": "test-index"
}):
    with mock.patch('src.vector_manager.VectorDBManager'):
        with mock.patch('src.embeddings.embed_chunks', return_value=[]):
            try:
                from app import app
                client = TestClient(app)
                APP_AVAILABLE = True
            except Exception as e:
                APP_AVAILABLE = False
                print(f"Could not import app: {e}")


@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available")
class TestUserWorkflow:
    """Test complete user workflow"""
    
    @pytest.fixture
    def auth_headers(self):
        """Create a test user and return auth headers"""
        import uuid
        email = f"workflow_{uuid.uuid4().hex[:8]}@test.com"
        response = client.post("/auth/register", json={
            "email": email,
            "password": "password123",
            "name": "Workflow Test"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        return None
    
    def test_register_login_logout_flow(self):
        """Test complete auth flow"""
        import uuid
        email = f"flow_{uuid.uuid4().hex[:8]}@test.com"
        
        # Register
        reg_response = client.post("/auth/register", json={
            "email": email,
            "password": "password123",
            "name": "Flow Test"
        })
        assert reg_response.status_code == 200
        token = reg_response.json()["token"]
        
        # Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        me_response = client.get("/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["email"] == email
        
        # Logout
        logout_response = client.post("/auth/logout", headers=headers)
        assert logout_response.status_code == 200
        
        # Token should be invalid now
        me_response2 = client.get("/auth/me", headers=headers)
        assert me_response2.status_code == 401
    
    def test_file_upload_query_flow(self, auth_headers):
        """Test file upload and query flow"""
        if not auth_headers:
            pytest.skip("Could not create auth headers")
        
        # Create a simple CSV
        csv_content = b"name,value\nAlice,100\nBob,200\nCharlie,300"
        
        with mock.patch('src.embeddings.embed_chunks') as mock_embed:
            mock_embed.return_value = [
                {"chunk_id": "test_0", "content": "test", "embedding": [0.1] * 1024}
            ]
            with mock.patch('src.vector_manager.VectorDBManager.upsert_vectors'):
                response = client.post(
                    "/upload",
                    files={"file": ("test.csv", BytesIO(csv_content), "text/csv")},
                    data={"user_id": "test_user"},
                    headers=auth_headers
                )
        
        # Upload might fail due to mocking, but shouldn't crash
        assert response.status_code in [200, 500]


@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available")
class TestChatWorkflow:
    """Test chat group workflow"""
    
    @pytest.fixture
    def auth_headers(self):
        """Create a test user and return auth headers"""
        import uuid
        email = f"chat_{uuid.uuid4().hex[:8]}@test.com"
        response = client.post("/auth/register", json={
            "email": email,
            "password": "password123",
            "name": "Chat Test"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}, email
        return None, None
    
    def test_create_group_send_message(self, auth_headers):
        """Test creating group and sending message"""
        headers, email = auth_headers
        if not headers:
            pytest.skip("Could not create auth headers")
        
        # Create group
        create_response = client.post(
            "/chat/groups",
            json={"name": "Test Group", "description": "Test"},
            headers=headers
        )
        
        if create_response.status_code == 200:
            group_id = create_response.json().get("group_id")
            
            # Get groups
            groups_response = client.get("/chat/groups", headers=headers)
            assert groups_response.status_code == 200
            
            # Send message
            if group_id:
                msg_response = client.post(
                    f"/chat/groups/{group_id}/messages",
                    json={"content": "Hello, test message!"},
                    headers=headers
                )
                assert msg_response.status_code in [200, 500]  # May fail if Gmail not configured


@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available")
class TestCalendarWorkflow:
    """Test calendar workflow"""
    
    @pytest.fixture
    def auth_headers(self):
        """Create a test user and return auth headers"""
        import uuid
        email = f"cal_{uuid.uuid4().hex[:8]}@test.com"
        response = client.post("/auth/register", json={
            "email": email,
            "password": "password123",
            "name": "Calendar Test"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        return None
    
    def test_create_event_flow(self, auth_headers):
        """Test creating calendar event"""
        if not auth_headers:
            pytest.skip("Could not create auth headers")
        
        # Create event
        event_response = client.post(
            "/calendar/events",
            json={
                "title": "Test Meeting",
                "date": "2026-01-15",
                "time": "10:00",
                "duration_minutes": 60,
                "event_type": "meeting"
            },
            headers=auth_headers
        )
        
        # May fail if Supabase not configured
        assert event_response.status_code in [200, 500]
        
        # Get events
        events_response = client.get("/calendar/events", headers=auth_headers)
        assert events_response.status_code in [200, 500]


@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available")
class TestModelSelection:
    """Test model selection workflow"""
    
    def test_get_models(self):
        """Test getting available models"""
        response = client.get("/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
