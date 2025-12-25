import pytest
from src.utils.validation import validate_isrc, sanitize_isrc
from src.core import yellberus

class TestISRCValidationMutation:
    """
    Robustness tests for ISRC validation and sanitization.
    Law 1: Separate Intent (Robustness).
    """

    def test_isrc_null_bytes(self):
        """Test ISRC with null bytes."""
        # Should return False or handle gracefully, not crash
        assert validate_isrc("US-AB1\0-23-45678") is False
        assert sanitize_isrc("US-AB1\0-23-45678") == "USAB1\x002345678" # \0 is not stripped by [-\s], but it shouldn't crash

    def test_isrc_exhaustion(self):
        """Test huge ISRC string (exhaustion)."""
        huge_isrc = "US" + "A" * 100000
        # Should not hang or crash
        assert validate_isrc(huge_isrc) is False
        
        sanitized = sanitize_isrc(huge_isrc)
        assert len(sanitized) == 100002

    def test_isrc_sql_injection_attempt(self):
        """Test SQL injection-like strings."""
        # These are just strings to the validator, should return False
        injection = "'; DROP TABLE Songs--"
        assert validate_isrc(injection) is False
        
        # Sanitization should treat them as normal chars (except dashes/spaces)
        # '; DROP TABLE Songs-- -> ';DROPTABLESONGS' (uppercase, dashes stripped)
        expected = "';DROPTABLESONGS"
        assert sanitize_isrc(injection) == expected

    def test_isrc_unicode_emoji(self):
        """Test Unicode and Emoji in ISRC."""
        emoji_isrc = "US-AB1-23-45678-🦕"
        assert validate_isrc(emoji_isrc) is False
        
        # Sanitization preserves the emoji if not dash/space
        # But typically ID3 tags might be latin1 or utf8. 
        # The function uses regex \w replacement? No, re.sub(r'[-\s]', '', isrc)
        assert "🦕" in sanitize_isrc(emoji_isrc)

    def test_isrc_none_handling(self):
        """Test None input."""
        assert validate_isrc(None) is False
        assert sanitize_isrc(None) == ""

    def test_isrc_empty_handling(self):
        """Test empty string."""
        assert validate_isrc("") is False
        assert sanitize_isrc("") == ""

    def test_yellberus_pattern_fallback(self, monkeypatch):
        """
        Test that validate_isrc falls back to default pattern 
        if Yellberus field is missing/misconfigured.
        """
        # Mock get_field to return None
        monkeypatch.setattr(yellberus, 'get_field', lambda x: None)
        
        # Should still work with default hardcoded pattern
        assert validate_isrc("US-AB1-23-45678") is True
        assert validate_isrc("INVALID") is False
