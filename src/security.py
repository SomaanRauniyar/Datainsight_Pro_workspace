"""
Security Module for DataInsight Pro
Implements security best practices to prevent common attacks
"""
import re
import html
import secrets
import hashlib
from typing import Optional, Any
from functools import wraps
import time


# ============== Input Sanitization ==============

def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize string input to prevent XSS and injection attacks
    """
    if not isinstance(value, str):
        return str(value)[:max_length]
    
    # Truncate to max length
    value = value[:max_length]
    
    # HTML escape to prevent XSS
    value = html.escape(value)
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    return value


def sanitize_email(email: str) -> Optional[str]:
    """
    Validate and sanitize email address
    Returns None if invalid
    """
    if not email or not isinstance(email, str):
        return None
    
    email = email.strip().lower()
    
    # Basic email regex validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return None
    
    # Check length
    if len(email) > 254:
        return None
    
    return email


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks
    """
    if not filename:
        return "unnamed"
    
    # Remove path separators and dangerous characters
    filename = re.sub(r'[/\\:*?"<>|]', '_', filename)
    
    # Remove leading dots (hidden files)
    filename = filename.lstrip('.')
    
    # Remove path traversal attempts
    filename = filename.replace('..', '')
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename or "unnamed"


def sanitize_sql_identifier(identifier: str) -> str:
    """
    Sanitize SQL identifiers (table names, column names)
    Only allows alphanumeric and underscore
    """
    return re.sub(r'[^a-zA-Z0-9_]', '', identifier)


# ============== Rate Limiting ==============

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self._requests = {}  # {key: [(timestamp, count)]}
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def is_allowed(self, key: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
        """
        Check if request is allowed under rate limit
        """
        now = time.time()
        
        # Periodic cleanup
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup()
            self._last_cleanup = now
        
        if key not in self._requests:
            self._requests[key] = []
        
        # Remove old entries
        cutoff = now - window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        
        # Check limit
        if len(self._requests[key]) >= max_requests:
            return False
        
        # Record request
        self._requests[key].append(now)
        return True
    
    def _cleanup(self):
        """Remove old entries"""
        now = time.time()
        cutoff = now - 3600  # 1 hour
        
        keys_to_remove = []
        for key, timestamps in self._requests.items():
            self._requests[key] = [t for t in timestamps if t > cutoff]
            if not self._requests[key]:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit(key: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
    """Check if request is within rate limit"""
    return rate_limiter.is_allowed(key, max_requests, window_seconds)


# ============== Token Security ==============

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure token"""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash a token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()


# ============== Password Security ==============

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if len(password) > 128:
        return False, "Password too long"
    
    # Check for common weak passwords
    weak_passwords = [
        'password', '12345678', 'qwerty123', 'admin123',
        'letmein', 'welcome', 'monkey', 'dragon'
    ]
    if password.lower() in weak_passwords:
        return False, "Password is too common"
    
    return True, ""


# ============== Content Security ==============

def is_safe_url(url: str) -> bool:
    """Check if URL is safe (no javascript:, data:, etc.)"""
    if not url:
        return False
    
    url_lower = url.lower().strip()
    
    dangerous_schemes = ['javascript:', 'data:', 'vbscript:', 'file:']
    for scheme in dangerous_schemes:
        if url_lower.startswith(scheme):
            return False
    
    return True


def sanitize_json_output(data: Any) -> Any:
    """
    Sanitize data before JSON serialization
    Removes sensitive fields and sanitizes strings
    """
    sensitive_fields = ['password', 'token', 'secret', 'api_key', 'private_key']
    
    if isinstance(data, dict):
        return {
            k: '[REDACTED]' if k.lower() in sensitive_fields else sanitize_json_output(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_json_output(item) for item in data]
    elif isinstance(data, str):
        return sanitize_string(data, max_length=50000)
    else:
        return data


# ============== Request Validation ==============

def validate_content_type(content_type: str, allowed: list[str]) -> bool:
    """Validate content type is in allowed list"""
    if not content_type:
        return False
    
    # Extract main type (ignore charset, etc.)
    main_type = content_type.split(';')[0].strip().lower()
    return main_type in [t.lower() for t in allowed]


def validate_file_extension(filename: str, allowed: list[str]) -> bool:
    """Validate file extension is in allowed list"""
    if not filename or '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in [e.lower().lstrip('.') for e in allowed]


# ============== Security Headers ==============

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def get_security_headers() -> dict:
    """Get security headers to add to responses"""
    return SECURITY_HEADERS.copy()
