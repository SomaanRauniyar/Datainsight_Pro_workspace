# src/llm.py
from groq import Groq
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env at module import time
for p in [Path(__file__).parent.parent / ".env", Path.cwd() / ".env"]:
    if p.exists():
        load_dotenv(p, override=True)
        break

from src.config import GROQ_API_KEY

# ============== Available Models ==============
# All these models work with ONE Groq API key
# Updated Jan 2026 - removed deprecated models
AVAILABLE_MODELS = {
    "auto": {
        "name": "Auto (Smart Selection)",
        "description": "Automatically picks best model for each task",
        "speed": "varies",
        "quality": "optimal"
    },
    "llama-3.1-8b-instant": {
        "name": "Llama 3.1 8B",
        "description": "Fastest responses, good for quick queries",
        "speed": "fast",
        "quality": "good"
    },
    "llama-3.3-70b-versatile": {
        "name": "Llama 3.3 70B",
        "description": "Best quality, ideal for complex analysis",
        "speed": "medium",
        "quality": "excellent"
    },
    "llama3-70b-8192": {
        "name": "Llama 3 70B",
        "description": "Powerful, great for detailed analysis",
        "speed": "medium",
        "quality": "excellent"
    },
    "llama3-8b-8192": {
        "name": "Llama 3 8B",
        "description": "Fast and efficient",
        "speed": "fast",
        "quality": "good"
    },
    "gemma2-9b-it": {
        "name": "Gemma 2 9B",
        "description": "Efficient, optimized for conversations",
        "speed": "fast",
        "quality": "good"
    },
    "mixtral-8x7b-32768": {
        "name": "Mixtral 8x7B",
        "description": "Great for code and technical tasks",
        "speed": "medium",
        "quality": "very good"
    }
}

# Task type → Best model mapping for Auto mode
# Default model: llama-3.1-8b-instant (fast and reliable)
DEFAULT_MODEL = "llama-3.1-8b-instant"

TASK_MODEL_MAP = {
    "quick_query": "llama-3.1-8b-instant",
    "analysis": "llama-3.1-8b-instant",  # Use fast model by default
    "meeting_prep": "llama-3.1-8b-instant",
    "executive_summary": "llama-3.1-8b-instant",
    "visualization": "llama-3.1-8b-instant",
    "chat": "llama-3.1-8b-instant",
    "code": "llama-3.1-8b-instant",
}

# Default client using system key
_default_client = None

def get_default_client():
    global _default_client
    if _default_client is None:
        # Try loading from env
        api_key = os.getenv("GROQ_API_KEY")
        
        # If not found, try loading dotenv
        if not api_key:
            from dotenv import load_dotenv
            from pathlib import Path
            # Try multiple paths
            for p in [Path(__file__).parent.parent / ".env", Path.cwd() / ".env"]:
                if p.exists():
                    load_dotenv(p, override=True)
                    break
            api_key = os.getenv("GROQ_API_KEY")
        
        if api_key and len(api_key) > 10:
            _default_client = Groq(api_key=api_key)
            print(f"[LLM] Default client initialized with system key")
        else:
            print(f"[LLM] Warning: No GROQ_API_KEY found in environment")
    
    return _default_client


def get_available_models():
    """Return list of available models for frontend"""
    return AVAILABLE_MODELS


def detect_task_type(prompt: str) -> str:
    """
    Analyze prompt to determine task type for auto model selection.
    Returns task type string.
    """
    prompt_lower = prompt.lower()
    
    # Check for visualization keywords
    if any(w in prompt_lower for w in ["chart", "graph", "plot", "visualize", "bar", "pie", "line chart"]):
        return "visualization"
    
    # Check for meeting/prep keywords
    if any(w in prompt_lower for w in ["meeting", "talking points", "prepare", "agenda", "presentation"]):
        return "meeting_prep"
    
    # Check for summary keywords
    if any(w in prompt_lower for w in ["summary", "summarize", "executive", "brief", "overview", "highlights"]):
        return "executive_summary"
    
    # Check for code keywords
    if any(w in prompt_lower for w in ["code", "function", "script", "program", "debug", "error"]):
        return "code"
    
    # Check for analysis keywords
    if any(w in prompt_lower for w in ["analyze", "trend", "pattern", "insight", "compare", "correlation", "forecast"]):
        return "analysis"
    
    # Long prompts usually need better models
    if len(prompt) > 1500:
        return "analysis"
    
    # Short prompts = quick query
    if len(prompt) < 200:
        return "quick_query"
    
    # Default
    return "chat"


def get_model_for_task(prompt: str, user_preference: str = "auto") -> tuple:
    """
    Get appropriate model based on user preference and task.
    
    Returns: (model_name, task_type)
    """
    # If user chose a specific model (not auto), use it
    if user_preference and user_preference != "auto":
        # Validate model exists and isn't deprecated
        if user_preference in AVAILABLE_MODELS and user_preference != "auto":
            return (user_preference, "user_selected")
        else:
            # Invalid/deprecated model, fall back to default
            print(f"[LLM] Model {user_preference} not available, using default")
            return (DEFAULT_MODEL, "fallback")
    
    # Auto mode - just use the default fast model for everything
    # This keeps it simple and reliable
    return (DEFAULT_MODEL, "auto")


def ask_llm(prompt: str, model: str = "auto", user_id: str = None):
    """
    Call Groq's LLM with smart model selection.
    
    Args:
        prompt: The prompt to send
        model: "auto" for smart selection, or specific model name
        user_id: Optional user ID to check for user's own API key
    
    Returns:
        LLM response content as string
    """
    # Resolve model (handle "auto" mode)
    actual_model, task_type = get_model_for_task(prompt, model)
    
    client = None
    key_source = "none"
    user_key = None
    
    # Try to use user's key if provided
    if user_id:
        try:
            from src.user_keys import get_effective_key
            user_key = get_effective_key(user_id, "groq_api_key")
            if user_key and len(user_key) > 10:
                client = Groq(api_key=user_key)
                key_source = "user"
                print(f"[LLM] Using user's Groq key for {user_id[:20]}...")
        except Exception as e:
            print(f"[LLM] Error getting user key: {e}")
    
    # Fall back to default client (system key from .env)
    if client is None:
        client = get_default_client()
        if client:
            key_source = "system"
            print(f"[LLM] Using system Groq key")
    
    # Last resort - try loading from env directly
    if client is None:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if api_key and len(api_key) > 10:
            client = Groq(api_key=api_key)
            key_source = "env_direct"
            print(f"[LLM] Using Groq key from direct env load")
    
    if client is None:
        print(f"[LLM] ERROR: No Groq API key available!")
        raise ValueError("No Groq API key available. Please add your Groq API key in Settings or contact admin.")
    
    print(f"[LLM] Model: {actual_model}, Task: {task_type}, Key: {key_source}")
    
    # Try the request, fall back to system key if user key fails
    try:
        response = client.chat.completions.create(
            model=actual_model,
            messages=[
                {"role": "system", "content": "You are BizAnalyst AI, a professional business analyst assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e).lower()
        
        # If model is decommissioned, try with a fallback model
        if "decommissioned" in error_msg or "deprecated" in error_msg:
            print(f"[LLM] Model {actual_model} is deprecated, trying llama-3.3-70b-versatile...")
            fallback_model = "llama-3.3-70b-versatile"
            try:
                response = client.chat.completions.create(
                    model=fallback_model,
                    messages=[
                        {"role": "system", "content": "You are BizAnalyst AI, a professional business analyst assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                return response.choices[0].message.content
            except Exception as e2:
                print(f"[LLM] Fallback model also failed: {e2}")
        
        # If user key failed, try system key as fallback
        if key_source == "user" and ("invalid" in error_msg or "api key" in error_msg or "authentication" in error_msg or "rate" in error_msg or "quota" in error_msg or "decommissioned" in error_msg):
            print(f"[LLM] User key failed ({e}), falling back to system key...")
            system_client = get_default_client()
            if system_client:
                try:
                    response = system_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",  # Use known working model
                        messages=[
                            {"role": "system", "content": "You are BizAnalyst AI, a professional business analyst assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2
                    )
                    return response.choices[0].message.content
                except Exception as e3:
                    print(f"[LLM] System key also failed: {e3}")
        
        # Re-raise if we can't recover
        print(f"[LLM] Error: {e}")
        raise


def ask_llm_with_model_info(prompt: str, model: str = "auto", user_id: str = None) -> dict:
    """
    Same as ask_llm but returns model info along with response.
    Useful for showing user which model was used.
    """
    actual_model, task_type = get_model_for_task(prompt, model)
    
    client = None
    using_user_key = False
    
    if user_id:
        try:
            from src.user_keys import get_effective_key
            user_key = get_effective_key(user_id, "groq_api_key")
            if user_key:
                client = Groq(api_key=user_key)
                using_user_key = True
        except:
            pass
    
    if client is None:
        client = get_default_client()
    
    if client is None:
        raise ValueError("No Groq API key available")
    
    response = client.chat.completions.create(
        model=actual_model,
        messages=[
            {"role": "system", "content": "You are BizAnalyst AI, a professional business analyst assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    
    return {
        "content": response.choices[0].message.content,
        "model_used": actual_model,
        "task_type": task_type,
        "using_user_key": using_user_key
    }


def ask_llm_with_key(prompt: str, api_key: str, model: str = "auto"):
    """
    Call Groq's LLM with a specific API key.
    """
    actual_model, _ = get_model_for_task(prompt, model)
    client = Groq(api_key=api_key)
    
    response = client.chat.completions.create(
        model=actual_model,
        messages=[
            {"role": "system", "content": "You are BizAnalyst AI, a professional business analyst assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content