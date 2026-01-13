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
        """
        Triggers if it's a Spotify paste:
        1. Ends with a comma (CamelCase instruction)
        2. Contains a comma in the middle (Standard list)
        """
        if not text:
            return False
        return text.endswith(',') or (',' in text)

    def split_camel_case(self, text: str) -> List[str]:
        """
        Handles exactly two cases for predictable behavior:
        1. Ends with ',' -> Split by internal commas AND then look for smashed [lower][Upper] junctions.
        2. Middle ',' only -> Perform standard comma splitting ONLY.
        """
        if not text:
            return []
            
        is_smash_requested = text.endswith(',')
        clean_text = text[:-1] if is_smash_requested else text
        
        # Always split by delimiters first
        import re
        chunks = [c.strip() for c in re.split(r'[,;]', clean_text) if c.strip()]
        
        if not is_smash_requested:
            # Case 2: Standard List Split (no CamelCase chopping)
            return chunks
            
        # Case 1: CamelCase Split (BobJohnBill, -> Bob, John, Bill)
        results = []
        for chunk in chunks:
            current = ""
            for i, char in enumerate(chunk):
                current += char
                if i < len(chunk) - 1:
                    # Split at smash point: [lower][Upper]
                    if char.islower() and chunk[i+1].isupper():
                        results.append(current.strip())
                        current = ""
            if current.strip():
                results.append(current.strip())
        
        return [r for r in results if r]

    def get_preview(self, text: str, limit: int = 3) -> str:
        """Get a human-readable preview of the split."""
        parts = self.split_camel_case(text)
        if not parts:
            return ""
        
        preview = ", ".join(parts[:limit])
        if len(parts) > limit:
            preview += "..."
        return preview
