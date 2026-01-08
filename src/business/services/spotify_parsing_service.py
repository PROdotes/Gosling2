"""
Spotify Parsing Service 🎵
Handles specific parsing logic for Spotify copy-pastes, such as CamelCase splitting.
"""
import re
from typing import List

class SpotifyParsingService:
    """
    Utility service for handling special user-workflow parsing logic.
    """
    
    def is_camel_case(self, text: str) -> bool:
        """Check if a string looks like a Spotify CamelCase paste."""
        if not text:
            return False
        # Trailing comma OR standard CamelCase (lower followed by Upper)
        if text.endswith(','):
            return True
        return bool(re.search(r'[a-z][A-Z]', text))

    def split_camel_case(self, text: str) -> List[str]:
        """
        Split a CamelCase string into separate words.
        Example: "AlfBobJohn" -> ["Alf", "Bob", "John"]
        """
        if not text:
            return []
            
        # Strip trailing comma if used as a directive
        clean_text = text[:-1] if text.endswith(',') else text
            
        # Regex to find all words starting with an uppercase letter
        # Handles cases like "JohnWick" -> ["John", "Wick"]
        parts = re.findall(r'[A-Z][^A-Z]*', clean_text)
        
        # Strip whitespace just in case
        return [p.strip() for p in parts if p.strip()]
