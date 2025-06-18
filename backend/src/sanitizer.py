"""
Input sanitization utilities for preventing XSS attacks
"""

import bleach
from typing import Optional


def sanitize_text(text: Optional[str], allow_html: bool = False) -> Optional[str]:
    """
    Sanitize user input to prevent XSS attacks.
    
    Args:
        text: The text to sanitize
        allow_html: Whether to allow basic HTML formatting (default: False)
        
    Returns:
        Sanitized text or None if input was None
    """
    if text is None:
        return None
    
    if not allow_html:
        # Strip all HTML tags for plain text
        return bleach.clean(text, tags=[], strip=True)
    else:
        # Allow only safe tags for formatted text
        allowed_tags = ['b', 'i', 'u', 'strong', 'em', 'p', 'br']
        allowed_attributes = {}
        return bleach.clean(
            text,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )


def sanitize_quest_title(title: str) -> str:
    """Sanitize quest title - no HTML allowed"""
    return sanitize_text(title, allow_html=False) or ""


def sanitize_quest_description(description: str) -> str:
    """Sanitize quest description - basic formatting allowed"""
    return sanitize_text(description, allow_html=True) or ""


def sanitize_submission_text(text: str) -> str:
    """Sanitize submission text - no HTML allowed"""
    return sanitize_text(text, allow_html=False) or ""


def sanitize_dispute_reason(reason: str) -> str:
    """Sanitize dispute reason - no HTML allowed"""
    return sanitize_text(reason, allow_html=False) or ""


def sanitize_attestation_notes(notes: Optional[str]) -> Optional[str]:
    """Sanitize attestation notes - no HTML allowed"""
    return sanitize_text(notes, allow_html=False)