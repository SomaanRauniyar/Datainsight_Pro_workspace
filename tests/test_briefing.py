"""
Tests for Briefing System Module
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_PATH"] = "data/test_datainsight.db"

from src.database import init_db, get_connection, create_user
from src.briefing_system import BriefingSystem
import unittest.mock as mock

@pytest.fixture(autouse=True)
def setup_db():
    """Setup fresh test database"""
    init_db()
    yield
    with get_connection() as conn:
        conn.execute("DELETE FROM briefings")
        conn.execute("DELETE FROM token_usage")
        conn.execute("DELETE FROM users")
        conn.commit()

@pytest.fixture
def test_user():
    """Create a test user"""
    user_id = create_user("brieftest@example.com", "password123", "Brief Tester")
    return user_id

class TestBriefingSystem:
    @mock.patch('src.briefing_system.ask_llm')
    def test_generate_executive_summary(self, mock_llm, test_user):
        mock_llm.return_value = '''
        {
            "bullets": [
                "Revenue increased by 15% this quarter",
                "Top product category is Electronics",
                "Recommend expanding to new markets"
            ],
            "headline": "Strong Q4 Performance"
        }
        '''
        
        result = BriefingSystem.generate_executive_summary(
            "Sample data content here",
            test_user
        )
        
        assert result["success"] == True
        assert "summary" in result
        assert len(result["summary"]["bullets"]) == 3
        assert result["summary"]["headline"] == "Strong Q4 Performance"
    
    @mock.patch('src.briefing_system.ask_llm')
    def test_generate_executive_summary_malformed_json(self, mock_llm, test_user):
        mock_llm.return_value = "This is just plain text response"
        
        result = BriefingSystem.generate_executive_summary(
            "Sample data",
            test_user
        )
        
        assert result["success"] == True
        # Should fallback to using response as single bullet
        assert "summary" in result
    
    @mock.patch('src.briefing_system.ask_llm')
    def test_generate_meeting_prep(self, mock_llm, test_user):
        mock_llm.return_value = '''
        {
            "talking_points": [
                {"point": "Q4 revenue exceeded targets", "type": "metric"},
                {"point": "What's the plan for Q1?", "type": "question"},
                {"point": "Market expansion strategy", "type": "topic"},
                {"point": "Finalize budget allocation", "type": "action"}
            ],
            "meeting_focus": "Quarterly Review"
        }
        '''
        
        result = BriefingSystem.generate_meeting_prep(
            "Quarterly business review meeting",
            "Revenue up 15%, costs down 5%",
            test_user
        )
        
        assert result["success"] == True
        assert "prep" in result
        assert len(result["prep"]["talking_points"]) == 4
        assert result["prep"]["meeting_focus"] == "Quarterly Review"
    
    @mock.patch('src.briefing_system.ask_llm')
    def test_briefing_saved_to_db(self, mock_llm, test_user):
        mock_llm.return_value = '{"bullets": ["Test"], "headline": "Test"}'
        
        BriefingSystem.generate_executive_summary("Test content", test_user)
        
        briefings = BriefingSystem.get_recent_briefings(test_user, "executive_summary")
        assert len(briefings) >= 1
        assert briefings[0]["type"] == "executive_summary"
    
    def test_get_recent_briefings_empty(self, test_user):
        briefings = BriefingSystem.get_recent_briefings(test_user)
        assert briefings == []
    
    @mock.patch('src.briefing_system.ask_llm')
    def test_generate_data_summary_for_upload(self, mock_llm, test_user):
        mock_llm.return_value = '''
        {
            "bullets": ["Data contains 100 rows", "3 numeric columns", "Consider filtering outliers"],
            "headline": "Sales Data Overview"
        }
        '''
        
        preview = [
            {"product": "A", "sales": 100},
            {"product": "B", "sales": 200}
        ]
        
        result = BriefingSystem.generate_data_summary_for_upload(
            preview, "sales.csv", test_user
        )
        
        assert result["success"] == True
        assert "summary" in result
    
    @mock.patch('src.briefing_system.ask_llm')
    def test_content_truncation(self, mock_llm, test_user):
        mock_llm.return_value = '{"bullets": ["Test"], "headline": "Test"}'
        
        # Create very long content
        long_content = "x" * 10000
        
        BriefingSystem.generate_executive_summary(long_content, test_user)
        
        # Check that the prompt was truncated
        call_args = mock_llm.call_args[0][0]
        assert len(call_args) < 10000

class TestBriefingEdgeCases:
    @mock.patch('src.briefing_system.ask_llm')
    def test_llm_error_handling(self, mock_llm, test_user):
        mock_llm.side_effect = Exception("LLM API Error")
        
        result = BriefingSystem.generate_executive_summary("Test", test_user)
        
        assert result["success"] == False
        assert "error" in result
    
    @mock.patch('src.briefing_system.ask_llm')
    def test_json_in_middle_of_response(self, mock_llm, test_user):
        mock_llm.return_value = '''
        Here is the summary:
        {"bullets": ["Point 1", "Point 2"], "headline": "Summary"}
        Hope this helps!
        '''
        
        result = BriefingSystem.generate_executive_summary("Test", test_user)
        
        assert result["success"] == True
        assert len(result["summary"]["bullets"]) == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
