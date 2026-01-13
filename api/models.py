"""
API Models - Pydantic models for request/response validation
"""
from pydantic import BaseModel, validator
from typing import Optional, List

# ============== Authentication Models ==============
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class ClerkSignInRequest(BaseModel):
    email: str
    password: str

class ClerkSignUpRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class ClerkCallbackRequest(BaseModel):
    session_token: str

# ============== Team Management Models ==============
class TeamMemberRequest(BaseModel):
    email: str

# ============== Email Models ==============
class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc_team: bool = True

class ReplyEmailRequest(BaseModel):
    thread_id: str
    body: str
    cc_team: bool = True

class EmailShareChartRequest(BaseModel):
    chart_json: str
    title: str = "Shared Chart"

# ============== Briefing Models ==============
class MeetingPrepRequest(BaseModel):
    context: str
    insights: str

# ============== User API Keys Models ==============
class SaveApiKeyRequest(BaseModel):
    key_name: str
    key_value: str

class TestApiKeyRequest(BaseModel):
    key_name: str

# ============== Model Preferences ==============
class ModelPreferenceRequest(BaseModel):
    model: str

# ============== Gmail Models ==============
class GmailTokensRequest(BaseModel):
    tokens: dict

# ============== Chat Models ==============
class CreateGroupRequest(BaseModel):
    name: str
    description: Optional[str] = None

class AddMemberRequest(BaseModel):
    email: str
    name: Optional[str] = None

class SendMessageRequest(BaseModel):
    content: str
    message_type: Optional[str] = "text"
    chart_json: Optional[str] = None
    chart_title: Optional[str] = None

class ShareChartRequest(BaseModel):
    group_id: int
    chart_json: str
    chart_title: str

# ============== Calendar Models ==============
class CreateEventRequest(BaseModel):
    title: str
    event_type: str = "meeting"
    date: str  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM
    duration_minutes: int = 60
    participants: List[str] = []
    description: Optional[str] = None

class UpdateEventRequest(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None

class AcceptSuggestionRequest(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    duration_minutes: Optional[int] = None

# ============== Response Models ==============
class UploadResponse(BaseModel):
    filename: str
    columns: List[str]
    preview: dict
    file_type: str
    message: str
    executive_summary: Optional[dict] = None

class QuickUploadResponse(BaseModel):
    filename: str
    preview: dict
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseModel):
    status: str
    progress: int
    message: str
    filename: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None