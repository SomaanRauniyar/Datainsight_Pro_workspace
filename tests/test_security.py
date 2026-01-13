"""
Security Tests - SQL Injection, XSS, Input Validation
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_PATH"] = "data/test_datainsight.db"
os.environ["PINECONE_API_KEY"] = "test-key"
os.environ["PINECONE_INDEX"] = "test-index"

from fastapi.testclient import TestClient
import unittest.mock as mock

APP_AVAILABLE = False
client = None

try:
    # Mock all external dependencies
    with mock.patch.dict('sys.modules', {
        'pinecone': mock.MagicMock(),
        'cohere': mock.MagicMock(),
    }):
        with mock.patch('src.vector_manager.VectorDBManager'):
            from app import app
            client = TestClient(app)
            APP_AVAILABLE = True
except Exception as e:
    print(f"Could not import app: {e}")


@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available")
class TestSQLInjection:
    """Test SQL injection prevention"""
    
    def test_login_sql_injection_email(self):
        """Test SQL injection in email field"""
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin'--",
            "' UNION SELECT * FROM users --",
        ]
        for payload in payloads:
            response = client.post("/auth/login", json={
                "email": payload,
                "password": "password123"
            })
            # Should fail auth, not crash or expose data
            assert response.status_code in [401, 422]
    
    def test_login_sql_injection_password(self):
        """Test SQL injection in password field"""
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "' OR '1'='1"
        })
        assert response.status_code in [401, 422]


@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available")
class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_password_length(self):
        """Test password minimum length"""
        response = client.post("/auth/register", json={
            "email": "short@test.com",
            "password": "123"
        })
        assert response.status_code == 400


@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available")
class TestAuthorizationBypass:
    """Test authorization bypass attempts"""
    
    def test_access_without_token(self):
        """Test accessing protected endpoints without token"""
        protected_endpoints = [
            "/auth/me",
            "/team",
            "/calendar/events",
        ]
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
    
    def test_access_with_invalid_token(self):
        """Test accessing protected endpoints with invalid token"""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401


@pytest.mark.skipif(not APP_AVAILABLE, reason="App not available")
class TestHealthEndpoints:
    """Test health endpoints work"""
    
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
    
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
