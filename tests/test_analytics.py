"""
Tests for Analytics Engine Module
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from src.analytics_engine import AnalyticsEngine

@pytest.fixture
def sample_df():
    """Create sample DataFrame for testing"""
    return pd.DataFrame({
        'product': ['A', 'B', 'C', 'A', 'B', 'C'],
        'region': ['North', 'South', 'North', 'South', 'North', 'South'],
        'sales': [100, 200, 150, 120, 180, 90],
        'quantity': [10, 20, 15, 12, 18, 9],
        'date': pd.date_range('2024-01-01', periods=6)
    })

@pytest.fixture
def numeric_df():
    """DataFrame with only numeric columns"""
    return pd.DataFrame({
        'x': np.random.randn(100),
        'y': np.random.randn(100),
        'z': np.random.randn(100)
    })

class TestAnalyticsEngine:
    def test_detect_column_types(self, sample_df):
        types = AnalyticsEngine.detect_column_types(sample_df)
        
        assert 'sales' in types['numerical']
        assert 'quantity' in types['numerical']
        assert 'product' in types['categorical']
        assert 'region' in types['categorical']
        assert 'date' in types['datetime']
    
    def test_detect_column_types_numeric_only(self, numeric_df):
        types = AnalyticsEngine.detect_column_types(numeric_df)
        
        assert len(types['numerical']) == 3
        assert len(types['categorical']) == 0
        assert len(types['datetime']) == 0
    
    def test_auto_visualize_bar(self, sample_df):
        result = AnalyticsEngine.auto_visualize(sample_df, "bar chart")
        
        assert result["success"] == True
        assert result["figure"] is not None
    
    def test_auto_visualize_pie(self, sample_df):
        result = AnalyticsEngine.auto_visualize(sample_df, "pie chart")
        
        assert result["success"] == True
        assert result["figure"] is not None
    
    def test_auto_visualize_scatter(self, numeric_df):
        result = AnalyticsEngine.auto_visualize(numeric_df, "scatter plot")
        
        assert result["success"] == True
        assert result["figure"] is not None
    
    def test_auto_visualize_histogram(self, sample_df):
        result = AnalyticsEngine.auto_visualize(sample_df, "histogram distribution")
        
        assert result["success"] == True
        assert result["figure"] is not None
    
    def test_auto_visualize_line(self, sample_df):
        result = AnalyticsEngine.auto_visualize(sample_df, "line trend")
        
        assert result["success"] == True
        assert result["figure"] is not None
    
    def test_get_data_insights(self, sample_df):
        insights = AnalyticsEngine.get_data_insights(sample_df)
        
        assert insights["row_count"] == 6
        assert insights["column_count"] == 5
        assert "sales" in insights["columns"]
        assert insights["columns"]["sales"]["type"] == "numerical"
        assert insights["columns"]["sales"]["min"] == 90
        assert insights["columns"]["sales"]["max"] == 200
    
    def test_get_data_insights_missing_values(self):
        df = pd.DataFrame({
            'a': [1, 2, None, 4],
            'b': ['x', None, 'y', 'z']
        })
        insights = AnalyticsEngine.get_data_insights(df)
        
        assert insights["columns"]["a"]["missing"] == 1
        assert insights["columns"]["b"]["missing"] == 1
    
    def test_clean_code(self):
        code_with_markdown = """```python
import pandas as pd
fig = px.bar(df, x='a', y='b')
fig.show()
```"""
        cleaned = AnalyticsEngine._clean_code(code_with_markdown)
        
        assert "```" not in cleaned
        assert "fig.show()" not in cleaned
        assert "px.bar" in cleaned
    
    def test_execute_plot_code_success(self, sample_df):
        code = """
fig = px.bar(df, x='product', y='sales', title='Sales by Product')
"""
        result = AnalyticsEngine.execute_plot_code(code, sample_df)
        
        assert result["success"] == True
        assert result["figure"] is not None
    
    def test_execute_plot_code_no_fig(self, sample_df):
        code = """
result = df['sales'].sum()
"""
        result = AnalyticsEngine.execute_plot_code(code, sample_df)
        
        assert result["success"] == False
        assert "fig" in result["error"].lower()
    
    def test_execute_plot_code_syntax_error(self, sample_df):
        code = """
fig = px.bar(df, x='product' y='sales')  # Missing comma
"""
        result = AnalyticsEngine.execute_plot_code(code, sample_df)
        
        assert result["success"] == False
        assert "error" in result

class TestAnalyticsEdgeCases:
    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = AnalyticsEngine.auto_visualize(df, "bar")
        
        assert result["success"] == False
    
    def test_single_column_df(self):
        df = pd.DataFrame({'values': [1, 2, 3, 4, 5]})
        result = AnalyticsEngine.auto_visualize(df, "histogram")
        
        assert result["success"] == True
    
    def test_categorical_only_df(self):
        df = pd.DataFrame({
            'cat1': ['a', 'b', 'c'],
            'cat2': ['x', 'y', 'z']
        })
        types = AnalyticsEngine.detect_column_types(df)
        
        assert len(types['categorical']) == 2
        assert len(types['numerical']) == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
