import re
import os
from typing import Dict, List, Optional, Any

class PatternEngine:
    """
    Central logic for processing Filename Patterns.
    Handles both 'Expansion' (Metadata -> Filename) and 'Extraction' (Filename -> Metadata).
    
    Tokens:
    - {Artist}: Performer(s) or Unified Artist
    - {Title}: Song Title
    - {Album}: Album Name
    - {Year}: Recording Year
    - {BPM}: Tempo
    - {Genre}: Genre (First if multiple)
    - {Ignore}: Wildcard (Extraction Only)
    """
    
    # Supported Tokens
    TOKENS = ["{Artist}", "{Title}", "{Album}", "{Year}", "{BPM}", "{Genre}", "{Publisher}"]
    
    # Token -> Regex Group Name map
    # We use TitleCase for UI tokens, lowercase for Yellberus fields (mostly)
    TOKEN_MAP = {
        "{Artist}": "performers",
        "{Title}": "title",
        "{Album}": "album",
        "{Year}": "recording_year",
        "{BPM}": "bpm",
        "{Genre}": "genre",
        "{Publisher}": "publisher",
    }

    # ==================== EXPANSION (Rename) ====================
    
    @staticmethod
    def resolve_pattern(pattern: str, data_context: Dict[str, Any]) -> str:
        """
        Replace tokens in pattern with data from context.
        context is a flat dict of pre-processed strings (Artist, Title, etc.)
        """
        result = pattern
        for token in PatternEngine.TOKENS:
            key = token.strip("{}") # e.g. "Artist"
            # Try exact key Match (Artist)
            val = data_context.get(key)
            if val is None:
                # Try lowercase (artist)
                val = data_context.get(key.lower())
                
            # Default to placeholder if missing? Or empty?
            # RenamingService usually handles sanitized extraction first.
            if val is None:
                val = "Unknown"
            
            result = result.replace(token, str(val))
            
        return result

    @staticmethod
    def sanitize_filename(text: str) -> str:
        """Sanitize text for use in filenames (Windows/Linux safe)."""
        if not text: return ""
        # Remove chars invalid in Windows
        bad_chars = '<>:"/\\|?*'
        clean = "".join(c for c in text if c not in bad_chars)
        # Strip trailing/leading spaces/dots (Windows hates 'Folder. ')
        return clean.strip().strip('.')

    # ==================== EXTRACTION (Parse) ====================

    @staticmethod
    def compile_extraction_regex(pattern: str) -> Optional[re.Pattern]:
        """
        Compile a user pattern like "{Artist} - {Title}" into a Regex.
        Handles {Ignore} token.
        """
        if not pattern: return None
        
        # 1. Escape special characters in the pattern (except our tokens)
        # We need to preserve the user's separators.
        
        # Strategy: 
        # a. Find all tokens (including unknown ones or {Ignore})
        # b. Escape everything BETWEEN tokens
        # c. Replace tokens with Named Capture Groups
        
        token_regex = re.compile(r'\{[a-zA-Z]+\}')
        tokens_found = [(m.start(), m.end(), m.group()) for m in token_regex.finditer(pattern)]
        
        if not tokens_found:
             return None # No tokens? Literal match only
             
        regex_str = "^"
        last_pos = 0
        
        for i, (start, end, token_str) in enumerate(tokens_found):
            # Text before this token (User Separator)
            prefix = pattern[last_pos:start]
            regex_str += re.escape(prefix)
            
            # Identify Group logic
            # Case-Insensitive Token Matching
            token_lower = token_str.lower()
            
            # Map canonical keys to lowercase for lookup
            # This allows {Title}, {TITLE}, {title} to all work
            lcase_map = {k.lower(): v for k, v in PatternEngine.TOKEN_MAP.items()}
            
            if token_lower == "{ignore}":
                # Non-capturing group, consume until next separator
                # Lazy match is safer for intermediates
                if i == len(tokens_found) - 1:
                    regex_str += r"(?:.+)" # Greedy at end
                else:
                    regex_str += r"(?:.+?)" 
            
            elif token_lower in lcase_map:
                field = lcase_map[token_lower]
                # If last token, generally greedy (.+) to capture rest of line
                if i == len(tokens_found) - 1:
                     regex_str += f"(?P<{field}>.+)"
                else:
                     # Non-lazy: This is tricky. 
                     # "{Artist} - {Title}" -> (.+?) - (.+) works fine.
                     regex_str += f"(?P<{field}>.+?)"
            else:
                # Unknown token -> Treat as literal text
                regex_str += re.escape(token_str)
                
            last_pos = end
            
        # Trailing text after last token
        suffix = pattern[last_pos:]
        regex_str += re.escape(suffix) + "$"
        
        try:
            return re.compile(regex_str, re.IGNORECASE)
        except re.error:
            return None

    @staticmethod
    def extract_metadata(filename: str, compiled_regex: re.Pattern) -> Dict[str, str]:
        """
        Run regex against filename and return dict of found fields.
        Keys are Yellberus internal names (performers, title, etc).
        """
        match = compiled_regex.match(filename)
        if match:
            return match.groupdict()
        return {}
