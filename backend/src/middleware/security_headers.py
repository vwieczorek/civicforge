"""
Security headers middleware for FastAPI
"""

from fastapi import Request
from fastapi.responses import Response
from typing import Callable
import logging

logger = logging.getLogger(__name__)


async def add_security_headers(request: Request, call_next: Callable) -> Response:
    """
    Add security headers to all responses
    """
    response = await call_next(request)
    
    # Strict Transport Security - enforce HTTPS
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Prevent clickjacking attacks
    response.headers["X-Frame-Options"] = "DENY"
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Enable XSS protection in older browsers
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Referrer Policy - don't leak referrer information
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions Policy (formerly Feature Policy)
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), "
        "camera=(), "
        "geolocation=(), "
        "gyroscope=(), "
        "magnetometer=(), "
        "microphone=(), "
        "payment=(), "
        "usb=()"
    )
    
    # Content Security Policy - prevent XSS and data injection
    # Note: This is a basic CSP. Adjust based on your needs
    if not response.headers.get("Content-Security-Policy"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "  # Allow inline styles for now
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://cognito-idp.*.amazonaws.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    
    # Remove server header to avoid version disclosure
    response.headers.pop("server", None)
    
    # Add custom security header
    response.headers["X-Powered-By"] = "CivicForge"
    
    return response


def get_security_headers() -> dict:
    """
    Get security headers as a dictionary for manual use
    """
    return {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        ),
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://cognito-idp.*.amazonaws.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
        "X-Powered-By": "CivicForge"
    }