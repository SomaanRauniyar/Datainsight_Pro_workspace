"""
Visualization Routes - Chart generation and natural language plotting
"""
from fastapi import APIRouter, Form, Query, HTTPException, Depends
from typing import Optional
import pandas as pd
import plotly.express as px

from src.analytics_engine import AnalyticsEngine
from src.visualization import recommend_visualizations, detect_column_types
from ..dependencies import get_current_user, get_data_cache

router = APIRouter()
legacy_router = APIRouter()  # For backward compatibility

def coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Safely coerce object columns to numeric where possible."""
    for c in df.columns:
        if df[c].dtype == object:
            try:
                df[c] = pd.to_numeric(df[c])
            except (ValueError, TypeError):
                pass
    return df

@router.post("/by-query")
def visualize_by_query(
    user_id: str = Form(...),
    file_id: str = Form(...),
    visualization_query: str = Form(...),
    x: Optional[str] = Form(None),
    y: Optional[str] = Form(None),
    aggregate: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
    data_cache: dict = Depends(get_data_cache)
):
    """Generate visualization based on query parameters"""
    effective_user_id = str(user["user_id"]) if user else user_id
    
    # Try multiple cache key combinations
    df = None
    for key in [(effective_user_id, file_id), (user_id, file_id)]:
        if key in data_cache:
            df = data_cache[key]
            break
    
    if df is None or df.empty:
        return {
            "plots": [], 
            "error": f"Data not found. Please re-upload the file. (Looking for user={effective_user_id}, file={file_id})"
        }
    
    def _parse_plot_query(q: str, df_cols):
        """Parse natural language query to determine chart type and columns"""
        ql = (q or "").lower()
        chart = "bar"
        if any(k in ql for k in ["line", "time series", "timeseries"]):
            chart = "line"
        elif "scatter" in ql:
            chart = "scatter"
        elif "pie" in ql:
            chart = "pie"
        elif "hist" in ql:
            chart = "histogram"
        
        import re
        x_col = None
        y_col = None
        m = re.search(r"x\s*[:=]\s*([a-zA-Z0-9_\- ]+)", ql)
        if m:
            x_col = m.group(1).strip()
        m = re.search(r"y\s*[:=]\s*([a-zA-Z0-9_\- ]+)", ql)
        if m:
            y_col = m.group(1).strip()
        if x_col is None and y_col is None:
            m = re.search(r"([a-zA-Z0-9_\- ]+)\s*(vs|by)\s*([a-zA-Z0-9_\- ]+)", ql)
            if m:
                left, _, right = m.groups()
                x_col, y_col = left.strip(), right.strip()
        
        def _resolve(name):
            if not name:
                return None
            for c in df_cols:
                if c.lower() == name.lower():
                    return c
            return None
        
        x_col = _resolve(x_col)
        y_col = _resolve(y_col)
        return chart, x_col, y_col

    try:
        df = coerce_numeric_columns(df)
        types = detect_column_types(df)
        
        if not x and not y:
            chart, x, y = _parse_plot_query(visualization_query, df.columns)
        else:
            chart, _, _ = _parse_plot_query(visualization_query, df.columns)
        
        if x is None:
            x = (types["categorical"][0] if types["categorical"] else
                 types["datetime"][0] if types["datetime"] else df.columns[0])
        if y is None:
            y = (types["numerical"][0] if types["numerical"] else None)

        x_list = [c.strip() for c in (x.split(",") if isinstance(x, str) else [x]) if c]
        for xv in x_list:
            if xv not in df.columns:
                return {"plots": [], "error": f"Column not found for x: {xv}"}
        if y and y not in df.columns:
            return {"plots": [], "error": f"Column not found for y: {y}"}
        
        agg_fn = (aggregate or "sum").lower()
        if agg_fn not in ("sum", "mean", "count"):
            agg_fn = "sum"
        
        figs = []
        if chart == "line" and y and x_list:
            for xv in x_list:
                figs.append(px.line(df, x=xv, y=y, title=f"{y} over {xv}"))
        elif chart == "scatter" and y and x_list:
            for xv in x_list:
                figs.append(px.scatter(df, x=xv, y=y, title=f"{y} vs {xv}"))
        elif chart == "pie" and y and x_list:
            xv = x_list[0]
            if y == xv:
                agg_df = df.groupby(xv).size().reset_index(name="count")
                figs.append(px.pie(agg_df, names=xv, values="count", title=f"count by {xv}"))
            else:
                grouped = df.groupby(xv)[y]
                if agg_fn == "mean":
                    agg_df = grouped.mean().reset_index()
                elif agg_fn == "count":
                    agg_df = grouped.count().reset_index()
                else:
                    agg_df = grouped.sum().reset_index()
                figs.append(px.pie(agg_df, names=xv, values=y, title=f"{y} by {xv}"))
        elif chart == "histogram" and (y or x):
            col = y or x_list[0]
            figs.append(px.histogram(df, x=col, title=f"Distribution of {col}"))
        elif y and x_list:
            xv = x_list[0]
            if y == xv:
                agg_df = df.groupby(xv).size().reset_index(name="count")
                figs.append(px.bar(agg_df, x=xv, y="count", title=f"count by {xv}"))
            else:
                grouped = df.groupby(xv)[y]
                if agg_fn == "mean":
                    agg_df = grouped.mean().reset_index()
                elif agg_fn == "count":
                    agg_df = grouped.count().reset_index()
                else:
                    agg_df = grouped.sum().reset_index()
                figs.append(px.bar(agg_df, x=xv, y=y, title=f"{y} by {xv}"))
        else:
            figs = recommend_visualizations(df)
        
        return {"plots": [fig.to_json() for fig in figs]}
        
    except Exception as e:
        return {"plots": [], "error": f"Plot rendering failed: {str(e)}"}

@router.post("/nl")
def visualize_natural_language(
    user_id: str = Form(...),
    file_id: str = Form(...),
    query: str = Form(...),
    user: dict = Depends(get_current_user),
    data_cache: dict = Depends(get_data_cache)
):
    """Natural language visualization with self-correction"""
    try:
        effective_user_id = str(user["user_id"]) if user else user_id
        
        # Get DataFrame from cache
        df = data_cache.get((effective_user_id, file_id))
        if df is None:
            df = data_cache.get((user_id, file_id))
        
        if df is None or (hasattr(df, 'empty') and df.empty):
            raise HTTPException(status_code=404, detail="Data not found. Please upload a file first.")
        
        db_user_id = user["user_id"] if user else None
        result = AnalyticsEngine.generate_visualization(query, df, db_user_id)
        
        if result["success"]:
            return {
                "success": True,
                "plot": result["figure"].to_json(),
                "code": result.get("code", ""),
                "auto_generated": result.get("auto", False)
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Visualization failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visualization error: {str(e)}")

@router.get("/data/insights")
def get_data_insights(
    user_id: str = Query(...),
    file_id: str = Query(...),
    user: dict = Depends(get_current_user),
    data_cache: dict = Depends(get_data_cache)
):
    """Get statistical insights for uploaded data"""
    effective_user_id = str(user["user_id"]) if user else user_id
    df = data_cache.get((effective_user_id, file_id)) or data_cache.get((user_id, file_id))
    
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="Data not found")
    
    return AnalyticsEngine.get_data_insights(df)

# Legacy endpoints for backward compatibility
@legacy_router.post("/visualize_by_query")
def visualize_by_query_legacy(
    user_id: str = Form(...),
    file_id: str = Form(...),
    visualization_query: str = Form(...),
    x: Optional[str] = Form(None),
    y: Optional[str] = Form(None),
    aggregate: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
    data_cache: dict = Depends(get_data_cache)
):
    """Legacy visualization endpoint"""
    return visualize_by_query(user_id, file_id, visualization_query, x, y, aggregate, user, data_cache)

@legacy_router.post("/visualize/nl")
def visualize_natural_language_legacy(
    user_id: str = Form(...),
    file_id: str = Form(...),
    query: str = Form(...),
    user: dict = Depends(get_current_user),
    data_cache: dict = Depends(get_data_cache)
):
    """Legacy natural language visualization endpoint"""
    return visualize_natural_language(user_id, file_id, query, user, data_cache)

@legacy_router.get("/data/insights")
def get_data_insights_legacy(
    user_id: str = Query(...),
    file_id: str = Query(...),
    user: dict = Depends(get_current_user),
    data_cache: dict = Depends(get_data_cache)
):
    """Legacy data insights endpoint"""
    return get_data_insights(user_id, file_id, user, data_cache)