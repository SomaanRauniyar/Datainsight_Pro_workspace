"""
DataInsight Pro - FastAPI Backend Entry Point
🚀 MODULAR ARCHITECTURE - Clean, maintainable, recruiter-friendly codebase

This file now serves as a simple entry point that imports the modular application.
All routes, models, and logic have been organized into focused modules.

Architecture:
- api/main.py: Main FastAPI app with middleware
- api/routes/: Individual route modules by feature
- api/models.py: Pydantic models
- api/dependencies.py: Shared dependencies
"""

# Import the modular FastAPI application
from api.main import app

# Export for uvicorn
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )