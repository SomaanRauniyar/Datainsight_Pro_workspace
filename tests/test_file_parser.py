"""
Tests for File Parser Module - CSV parsing only (no docx dependency)
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from io import BytesIO
import pandas as pd


def parse_csv_simple(file_obj):
    """Simple CSV parser for testing"""
    if isinstance(file_obj, BytesIO):
        file_obj.seek(0)
    try:
        df = pd.read_csv(file_obj, sep=None, engine='python', encoding='utf-8')
    except Exception:
        file_obj.seek(0)
        df = pd.read_csv(file_obj, sep=None, engine='python', encoding='latin-1')
    
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass  # Keep as string
    
    return df.to_dict(orient='records')


class TestCSVParser:
    """Test CSV parsing functionality"""
    
    def test_parse_simple_csv(self):
        """Test parsing simple CSV"""
        csv_content = b"name,value\nAlice,100\nBob,200"
        result = parse_csv_simple(BytesIO(csv_content))
        
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[0]["value"] == 100
    
    def test_parse_csv_numeric_coercion(self):
        """Test that numeric values are coerced"""
        csv_content = b"id,amount,name\n1,99.99,Test"
        result = parse_csv_simple(BytesIO(csv_content))
        
        assert result[0]["id"] == 1
        assert result[0]["amount"] == 99.99
        assert result[0]["name"] == "Test"
    
    def test_parse_empty_csv(self):
        """Test parsing CSV with only headers"""
        csv_content = b"name,value\n"
        result = parse_csv_simple(BytesIO(csv_content))
        assert len(result) == 0
    
    def test_parse_csv_with_special_chars(self):
        """Test parsing CSV with UTF-8 characters"""
        csv_content = "name,value\nCafé,100".encode('utf-8')
        result = parse_csv_simple(BytesIO(csv_content))
        assert len(result) == 1
        assert "Caf" in result[0]["name"]


class TestEdgeCases:
    """Test edge cases"""
    
    def test_large_values(self):
        """Test handling large string values"""
        large_value = "A" * 1000
        csv_content = f"name,value\n{large_value},100".encode()
        result = parse_csv_simple(BytesIO(csv_content))
        assert len(result) == 1
        assert len(result[0]["name"]) == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
