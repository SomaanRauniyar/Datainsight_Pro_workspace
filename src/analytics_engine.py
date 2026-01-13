"""
Enhanced Analytics Engine for DataInsight Pro
Natural language plotting with self-correction capabilities
"""
import json
import re
import traceback
from typing import Dict, List, Optional, Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.llm import ask_llm
from src.database import log_token_usage

class AnalyticsEngine:
    """Advanced analytics with NL plotting and self-correction"""
    
    CODE_GEN_PROMPT = """
You are a Python data visualization expert. Generate Plotly code for the exact chart type the user requests.

AVAILABLE DATA:
- DataFrame 'df' with columns: {columns}
- Column types: {types}
- Sample data (first 3 rows): {sample}

USER REQUEST: {query}

IMPORTANT RULES:
1. Use plotly.express (imported as px) - it's simpler and more reliable
2. Store the figure in variable 'fig'
3. Do NOT call fig.show()
4. The dataframe 'df' already exists - just use it directly
5. If user asks for PIE chart, use px.pie()
6. If user asks for BAR chart, use px.bar()
7. If user asks for LINE chart, use px.line()
8. If user asks for SCATTER, use px.scatter()
9. For aggregations, use df.groupby().sum().reset_index() first
10. Keep code simple - just 1-3 lines maximum

EXAMPLES:
- Pie chart: agg = df.groupby('category')['value'].sum().reset_index(); fig = px.pie(agg, names='category', values='value', title='Values by Category')
- Bar chart: agg = df.groupby('name')['sales'].sum().reset_index(); fig = px.bar(agg, x='name', y='sales', title='Sales by Name')
- Line chart: fig = px.line(df, x='date', y='amount', title='Amount Over Time')

Return ONLY the Python code, nothing else:
"""

    FIX_CODE_PROMPT = """
The following Python visualization code produced an error:

CODE:
```python
{code}
```

ERROR:
{error}

AVAILABLE DATA:
- DataFrame 'df' with columns: {columns}

Fix the code to resolve the error. Return ONLY the corrected Python code, no explanations.
"""

    @staticmethod
    def detect_column_types(df: pd.DataFrame) -> Dict[str, List[str]]:
        """Categorize columns by data type"""
        types = {"numerical": [], "categorical": [], "datetime": []}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                types["numerical"].append(col)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                types["datetime"].append(col)
            else:
                # Try to parse as datetime
                try:
                    pd.to_datetime(df[col], errors='raise')
                    types["datetime"].append(col)
                except:
                    types["categorical"].append(col)
        return types
    
    @staticmethod
    def generate_plot_code(query: str, df: pd.DataFrame, user_id: int = None) -> str:
        """Generate Plotly code from natural language query"""
        types = AnalyticsEngine.detect_column_types(df)
        sample = df.head(3).to_dict(orient='records')
        
        prompt = AnalyticsEngine.CODE_GEN_PROMPT.format(
            columns=list(df.columns),
            types=types,
            sample=sample[:3],
            query=query
        )
        
        code = ask_llm(prompt, user_id=str(user_id) if user_id else None)
        
        if user_id:
            log_token_usage(user_id, len(prompt.split()) + len(code.split()), "code_generation")
        
        # Clean up code
        code = AnalyticsEngine._clean_code(code)
        return code
    
    @staticmethod
    def _clean_code(code: str) -> str:
        """Extract and clean Python code from LLM response"""
        # Remove markdown code blocks
        if "```python" in code:
            match = re.search(r"```python\s*(.*?)\s*```", code, re.DOTALL)
            if match:
                code = match.group(1)
        elif "```" in code:
            match = re.search(r"```\s*(.*?)\s*```", code, re.DOTALL)
            if match:
                code = match.group(1)
        
        # Remove fig.show() calls
        code = re.sub(r'fig\.show\(\)', '', code)
        
        return code.strip()
    
    @staticmethod
    def execute_plot_code(code: str, df: pd.DataFrame) -> Dict:
        """Safely execute plot code and return figure"""
        # Clean the code first
        code = code.strip()
        
        # Remove any markdown formatting
        if code.startswith('```'):
            lines = code.split('\n')
            code = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
        
        # Create safe execution environment
        safe_globals = {
            'pd': pd,
            'px': px,
            'go': go,
            'df': df.copy(),  # Use a copy to prevent modifications
            '__builtins__': {
                'len': len, 'range': range, 'list': list, 'dict': dict,
                'str': str, 'int': int, 'float': float, 'bool': bool,
                'sum': sum, 'min': min, 'max': max, 'sorted': sorted,
                'round': round, 'abs': abs, 'enumerate': enumerate,
                'zip': zip, 'map': map, 'filter': filter, 'print': print,
                'True': True, 'False': False, 'None': None
            }
        }
        local_vars = {}
        
        try:
            exec(code, safe_globals, local_vars)
            
            if 'fig' in local_vars:
                return {
                    "success": True,
                    "figure": local_vars['fig'],
                    "code": code
                }
            else:
                return {
                    "success": False,
                    "error": "Code did not produce a 'fig' variable",
                    "code": code
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "code": code
            }
    
    @staticmethod
    def fix_code(code: str, error: str, df: pd.DataFrame, user_id: int = None) -> str:
        """Ask LLM to fix broken code"""
        prompt = AnalyticsEngine.FIX_CODE_PROMPT.format(
            code=code,
            error=error,
            columns=list(df.columns)
        )
        
        fixed_code = ask_llm(prompt, user_id=str(user_id) if user_id else None)
        
        if user_id:
            log_token_usage(user_id, len(prompt.split()) + len(fixed_code.split()), "code_fix")
        
        return AnalyticsEngine._clean_code(fixed_code)
    
    @staticmethod
    def generate_visualization(query: str, df: pd.DataFrame, user_id: int = None, max_retries: int = 2) -> Dict:
        """Generate visualization with self-correction"""
        # Generate initial code
        code = AnalyticsEngine.generate_plot_code(query, df, user_id)
        
        # Try to execute
        result = AnalyticsEngine.execute_plot_code(code, df)
        
        # Self-correction loop
        retries = 0
        while not result["success"] and retries < max_retries:
            retries += 1
            fixed_code = AnalyticsEngine.fix_code(
                result["code"], 
                result.get("error", "Unknown error"),
                df,
                user_id
            )
            result = AnalyticsEngine.execute_plot_code(fixed_code, df)
        
        if result["success"]:
            return {
                "success": True,
                "figure": result["figure"],
                "code": result["code"],
                "retries": retries
            }
        else:
            # Fall back to automatic visualization
            return AnalyticsEngine.auto_visualize(df, query)
    
    @staticmethod
    def auto_visualize(df: pd.DataFrame, hint: str = "") -> Dict:
        """Automatic visualization based on data types"""
        try:
            types = AnalyticsEngine.detect_column_types(df)
            
            hint_lower = hint.lower() if hint else ""
            
            # Determine chart type from hint
            if "pie" in hint_lower and types["categorical"] and types["numerical"]:
                cat = types["categorical"][0]
                num = types["numerical"][0]
                agg = df.groupby(cat)[num].sum().reset_index()
                fig = px.pie(agg, names=cat, values=num, title=f"{num} by {cat}")
                return {"success": True, "figure": fig, "code": "# Auto-generated pie chart", "auto": True}
            
            elif "scatter" in hint_lower and len(types["numerical"]) >= 2:
                fig = px.scatter(df, x=types["numerical"][0], y=types["numerical"][1],
                               title=f"{types['numerical'][1]} vs {types['numerical'][0]}")
                return {"success": True, "figure": fig, "code": "# Auto-generated scatter plot", "auto": True}
            
            elif "line" in hint_lower or "trend" in hint_lower:
                if types["datetime"] and types["numerical"]:
                    fig = px.line(df, x=types["datetime"][0], y=types["numerical"][0],
                                title=f"{types['numerical'][0]} over time")
                    return {"success": True, "figure": fig, "code": "# Auto-generated line chart", "auto": True}
                elif types["numerical"]:
                    fig = px.line(df, y=types["numerical"][0], title=f"{types['numerical'][0]} trend")
                    return {"success": True, "figure": fig, "code": "# Auto-generated line chart", "auto": True}
            
            elif "hist" in hint_lower or "distribution" in hint_lower:
                if types["numerical"]:
                    fig = px.histogram(df, x=types["numerical"][0],
                                     title=f"Distribution of {types['numerical'][0]}")
                    return {"success": True, "figure": fig, "code": "# Auto-generated histogram", "auto": True}
            
            # Default: bar chart for categorical + numerical
            if types["categorical"] and types["numerical"]:
                cat = types["categorical"][0]
                num = types["numerical"][0]
                agg = df.groupby(cat)[num].sum().reset_index()
                # Limit to top 20 for readability
                if len(agg) > 20:
                    agg = agg.nlargest(20, num)
                fig = px.bar(agg, x=cat, y=num, title=f"{num} by {cat}")
                return {"success": True, "figure": fig, "code": "# Auto-generated bar chart", "auto": True}
            
            elif types["numerical"]:
                # Histogram for single numerical
                fig = px.histogram(df, x=types["numerical"][0],
                                 title=f"Distribution of {types['numerical'][0]}")
                return {"success": True, "figure": fig, "code": "# Auto-generated histogram", "auto": True}
            
            return {"success": False, "error": "Could not generate visualization for this data"}
            
        except Exception as e:
            return {"success": False, "error": f"Auto-visualization failed: {str(e)}"}
    
    @staticmethod
    def get_data_insights(df: pd.DataFrame, user_id: int = None) -> Dict:
        """Generate statistical insights from data"""
        insights = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": {}
        }
        
        types = AnalyticsEngine.detect_column_types(df)
        
        for col in df.columns:
            col_info = {
                "type": "numerical" if col in types["numerical"] else 
                        "datetime" if col in types["datetime"] else "categorical",
                "missing": int(df[col].isna().sum()),
                "unique": int(df[col].nunique())
            }
            
            if col in types["numerical"]:
                col_info.update({
                    "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                    "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                    "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                    "median": float(df[col].median()) if not pd.isna(df[col].median()) else None
                })
            elif col in types["categorical"]:
                top_values = df[col].value_counts().head(5).to_dict()
                col_info["top_values"] = {str(k): int(v) for k, v in top_values.items()}
            
            insights["columns"][col] = col_info
        
        return insights
