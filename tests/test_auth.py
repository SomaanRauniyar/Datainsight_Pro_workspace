"""
Tests for Authentication Module
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, get_connection
from src.auth import AuthService

# Use test database
os.environ["DATABASE_PATH"] = "data/test_datainsight.db"

@pytest.fixture(autouse=True)
def setup_db():
    """Setup fresh test database"""
    init_db()
    yield
    # Cleanup
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM users")
        conn.commit()

class TestAuthService:
    def test_register_success(self):
        result = AuthService.register("test@example.com", "password123", "Test User")
        assert result["success"] == True
        assert result["email"] == "test@example.com"
        assert "token" in result
        assert result["user_id"] is not None
    
    def test_register_duplicate_email(self):
        AuthService.register("dup@example.com", "password123")
        result = AuthService.register("dup@example.com", "password456")
        assert result["success"] == False
        assert "already registered" in result["error"].lower()
    
    def test_register_short_password(self):
        result = AuthService.register("short@example.com", "123")
        assert result["success"] == False
        assert "6 characters" in result["error"]
    
    def test_login_success(self):
        AuthService.register("login@example.com", "password123", "Login User")
        result = AuthService.login("login@example.com", "password123")
        assert result["success"] == True
        assert result["email"] == "login@example.com"
        assert "token" in result
    
    def test_login_wrong_password(self):
        AuthService.register("wrong@example.com", "password123")
        result = AuthService.login("wrong@example.com", "wrongpassword")
        assert result["success"] == False
        assert "invalid" in result["error"].lower()
    
    def test_login_nonexistent_user(self):
        result = AuthService.login("nonexistent@example.com", "password123")
        assert result["success"] == False
    
    def test_validate_token(self):
        reg_result = AuthService.register("token@example.com", "password123")
        token = reg_result["token"]
        
        user = AuthService.validate_token(token)
        assert user is not None
        assert user["email"] == "token@example.com"
    
    def test_validate_invalid_token(self):
        user = AuthService.validate_token("invalid_token_12345")
        assert user is None
    
    def test_logout(self):
        reg_result = AuthService.register("logout@example.com", "password123")
        token = reg_result["token"]
        
        # Token should be valid
        assert AuthService.validate_token(token) is not None
        
        # Logout
        AuthService.logout(token)
        
        # Token should be invalid now
        assert AuthService.validate_token(token) is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
