"""
Unit tests for ISRC validation utilities.

Tests the sanitize_isrc() and validate_isrc() functions that centralize
ISRC validation logic per PROPOSAL_DUPLICATE_DETECTION.md Phase 0.

Per TESTING.md:
- Logic tests (this file): Valid/invalid formats, sanitization behavior
- Robustness tests (test_validation_mutation.py): Null bytes, exhaustion, injection
"""

import pytest
from src.utils.validation import sanitize_isrc, validate_isrc


class TestSanitizeISRC:
    """Test ISRC sanitization (strip dashes, spaces, uppercase)."""
    
    def test_sanitize_with_dashes(self):
        """ISRC with dashes should be stripped."""
        assert sanitize_isrc("US-AB1-23-45678") == "USAB12345678"
    
    def test_sanitize_without_dashes(self):
        """ISRC without dashes should remain unchanged (except uppercase)."""
        assert sanitize_isrc("USAB12345678") == "USAB12345678"
    
    def test_sanitize_with_spaces(self):
        """ISRC with spaces should have spaces stripped."""
        assert sanitize_isrc("US AB1 23 45678") == "USAB12345678"
    
    def test_sanitize_lowercase(self):
        """Lowercase ISRC should be converted to uppercase."""
        assert sanitize_isrc("us-ab1-23-45678") == "USAB12345678"
    
    def test_sanitize_mixed_case(self):
        """Mixed case ISRC should be uppercased."""
        assert sanitize_isrc("Us-Ab1-23-45678") == "USAB12345678"
    
    def test_sanitize_empty_string(self):
        """Empty string should return empty string."""
        assert sanitize_isrc("") == ""
    
    def test_sanitize_none(self):
        """None should return empty string."""
        assert sanitize_isrc(None) == ""
    
    def test_sanitize_whitespace_only(self):
        """Whitespace-only string should return empty string."""
        assert sanitize_isrc("   ") == ""


class TestValidateISRC:
    """Test ISRC validation against Yellberus pattern."""
    
    def test_valid_isrc_no_dashes(self):
        """Valid ISRC without dashes should pass."""
        assert validate_isrc("USAB12345678") is True
    
    def test_valid_isrc_with_dashes(self):
        """Valid ISRC with dashes should pass (sanitized internally)."""
        assert validate_isrc("US-AB1-23-45678") is True
    
    def test_valid_isrc_lowercase(self):
        """Valid lowercase ISRC should pass (sanitized internally)."""
        assert validate_isrc("us-ab1-23-45678") is True
    
    def test_invalid_too_short(self):
        """ISRC too short should fail."""
        assert validate_isrc("USAB1234567") is False  # 11 chars instead of 12
    
    def test_invalid_too_long(self):
        """ISRC too long should fail."""
        assert validate_isrc("USAB123456789") is False  # 13 chars instead of 12
    
    def test_invalid_wrong_country_code(self):
        """ISRC with invalid country code should fail."""
        assert validate_isrc("1SAB12345678") is False  # Starts with digit
    
    def test_invalid_non_alphanumeric(self):
        """ISRC with special characters (after sanitization) should fail."""
        assert validate_isrc("US@AB1234567") is False
    
    def test_empty_string(self):
        """Empty string should fail validation."""
        assert validate_isrc("") is False
    
    def test_none(self):
        """None should fail validation."""
        assert validate_isrc(None) is False
    
    def test_whitespace_only(self):
        """Whitespace-only string should fail."""
        assert validate_isrc("   ") is False


class TestYellberusIntegration:
    """Test that ISRC field in Yellberus has validation_pattern set."""
    
    def test_isrc_field_has_validation_pattern(self):
        """ISRC field in Yellberus should have validation_pattern attribute."""
        from src.core.yellberus import get_field
        
        isrc_field = get_field('isrc')
        assert isrc_field is not None, "ISRC field not found in Yellberus"
        assert hasattr(isrc_field, 'validation_pattern'), "ISRC field missing validation_pattern attribute"
        assert isrc_field.validation_pattern is not None, "ISRC validation_pattern is None"
    
    def test_isrc_pattern_matches_expected(self):
        """ISRC validation pattern should match expected regex."""
        from src.core.yellberus import get_field
        
        isrc_field = get_field('isrc')
        # Pattern should be for sanitized format (no dashes)
        expected_pattern = r'^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$'
        assert isrc_field.validation_pattern == expected_pattern
