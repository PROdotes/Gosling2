"""
Validation utilities for metadata fields.

Centralizes validation logic to prevent code duplication across UI, service layer,
and duplicate detection. Per PROPOSAL_DUPLICATE_DETECTION.md Phase 0.
"""

import re
from typing import Optional


def sanitize_isrc(isrc: Optional[str]) -> str:
    """
    Sanitize ISRC by stripping dashes, spaces, and converting to uppercase.
    
    Args:
        isrc: ISRC string in any format (e.g., "US-AB1-23-45678" or "USAB12345678")
    
    Returns:
        Sanitized ISRC (e.g., "USAB12345678") or empty string if None/empty
    
    Examples:
        >>> sanitize_isrc("US-AB1-23-45678")
        'USAB12345678'
        >>> sanitize_isrc("us ab1 23 45678")
        'USAB12345678'
        >>> sanitize_isrc(None)
        ''
    """
    if not isrc:
        return ""
    
    # Strip everything except alphanumeric, convert to uppercase
    sanitized = re.sub(r'[^A-Z0-9]', '', str(isrc)).upper()
    
    return sanitized


def validate_isrc(isrc: Optional[str]) -> bool:
    """
    Validate ISRC against Yellberus pattern.
    
    ISRC format (sanitized): 2 letters (country) + 3 alphanumeric (registrant) 
                            + 2 digits (year) + 5 digits (designation)
    Example: USAB12345678
    
    Args:
        isrc: ISRC string to validate (can have dashes/spaces, will be sanitized)
    
    Returns:
        True if valid ISRC format, False otherwise
    
    Examples:
        >>> validate_isrc("US-AB1-23-45678")
        True
        >>> validate_isrc("USAB12345678")
        True
        >>> validate_isrc("invalid")
        False
    """
    if not isrc:
        return False
    
    # Sanitize first (strip dashes, spaces, uppercase)
    sanitized = sanitize_isrc(isrc)
    
    if not sanitized:
        return False
    
    # Get validation pattern from Yellberus (single source of truth)
    try:
        from src.core.yellberus import get_field
        
        field = get_field('isrc')
        if not field or not field.validation_pattern:
            # No pattern defined, fall back to default
            pattern = r'^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$'
        else:
            pattern = field.validation_pattern
    except Exception:
        # If Yellberus import fails, use default pattern
        pattern = r'^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$'
    
    # Validate against pattern
    return bool(re.match(pattern, sanitized))
