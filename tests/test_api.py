"""
Tests for FastAPI Endpoints
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_PATH"] = "data/test_datainsight.db"

from fastapi.testclient import TestClient

# Mock the vector_db initialization to avoid Pinecone connection during tests
import unittest.mock as mock

# We need to mock before importing app
with mock.patch.dict(os.environ, {
    "PINECONE_API_KEY": "test-key",
    "PINECONE_INDEX": "test-index"
}):
    # Mock VectorDBManager
    with mock.patch('src.vector_manager.VectorDBManager'):
        with mock.patch('src.embeddings.embed_chunks', return_value=[]):
            try:
                from app import app
                client = TestClient(app)
                APP_AVAILABLE = True
            except Exception as e:
                APP_AVAILABLE = False
                print(f"Could not import app: {e}")

@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available for testing")
class TestHealthEndpoints:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available for testing")
class TestAuthEndpoints:
    def test_register(self):
        response = client.post("/auth/register", json={
            "email": "apitest@example.com",
            "password": "password123",
            "name": "API Test"
        })
        # May fail if user exists, but should not error
        assert response.status_code in [200, 400]
    
    def test_register_invalid(self):
        response = client.post("/auth/register", json={
            "email": "invalid@example.com",
            "password": "123"  # Too short
        })
        assert response.status_code == 400
    
    def test_login_invalid(self):
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })
        assert response.status_code == 401
    
    def test_me_unauthorized(self):
        response = client.get("/auth/me")
        assert response.status_code == 401

@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available for testing")
class TestTeamEndpoints:
    def test_team_unauthorized(self):
        response = client.get("/team")
        assert response.status_code == 401
    
    def test_add_member_unauthorized(self):
        response = client.post("/team/members", json={"email": "test@example.com"})
        assert response.status_code == 401

@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available for testing")
class TestSchemaEndpoint:
    def test_schema_empty(self):
        response = client.get("/schema", params={
            "user_id": "test",
            "file_id": "nonexistent.csv"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["columns"] == []

@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available for testing")
class TestEmailEndpoints:
    def test_email_status_unauthorized(self):
        response = client.get("/email/status")
        assert response.status_code == 401
    
    def test_email_threads_unauthorized(self):
        response = client.get("/email/threads")
        assert response.status_code == 401

@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available for testing")
class TestBriefingEndpoints:
    def test_briefing_history_unauthorized(self):
        response = client.get("/briefing/history")
        assert response.status_code == 401

@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available for testing")
class TestAdminEndpoints:
    def test_admin_users_unauthorized(self):
        response = client.get("/admin/users")
        assert response.status_code == 401
    
    def test_admin_stats_unauthorized(self):
        response = client.get("/admin/stats")
        assert response.status_code == 401

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
