"""
Search Service

Handles web search URL generation and provider logic for external services.
Decouples URL formatting from UI widgets.
"""
import urllib.parse
from typing import Optional, List

class SearchService:
    """Service for generating search URLs."""
    
    PROVIDERS = ["Google", "Spotify", "YouTube", "MusicBrainz", "Discogs", "ZAMP"]

    def get_providers(self) -> List[str]:
        """Return list of supported search providers."""
        return self.PROVIDERS

    def get_search_url(self, provider: str, query_text: str) -> str:
        """Construct search URL based on provider."""
        if not query_text:
            return ""
            
        q_clean = urllib.parse.quote(query_text)
        
        if provider == "Google":
             return f"https://www.google.com/search?q={q_clean}"
        elif provider == "Spotify":
             return f"https://open.spotify.com/search/{q_clean}"
        elif provider == "YouTube":
             return f"https://www.youtube.com/results?search_query={q_clean}"
        elif provider == "MusicBrainz":
             return f"https://musicbrainz.org/search?query={q_clean}&type=release&method=indexed"
        elif provider == "Discogs":
             return f"https://www.discogs.com/search/?q={q_clean}&type=release"
        elif provider == "ZAMP":
             return f"https://www.zamp.hr/baza-autora/rezultati-djela/pregled/{q_clean}"
        
        return ""

    def construct_query(self, provider: str, title: str, artist: str = "", field_value: str = "", field_name: str = "") -> str:
        """
        Construct the optimal query string based on the provider and context.
        """

        if provider == "ZAMP" and not field_name:
            return title.strip() # ZAMP: Title Only
            
        # Default: Contextual
        return f"{artist} {title}".strip()

    def prepare_search(self, song, draft_values: dict, preferred_provider: str, field_def=None) -> str:
        """
        High-level entry point. 
        Decides EVERYTHING about the search (Provider, Context, Logic) given the raw inputs.
        
        Args:
            song: The source Song object (Domain Model)
            draft_values: Dictionary of current UI values {field_name: value}
            preferred_provider: The user's selected provider setting
            field_def: Optional FieldDef if clicking a micro-button
        """
        # 1. Resolve Effective Provider
        effective_provider = preferred_provider
        
        # Logic: If searching specific metadata (Composer, Lyrics, Year), Force Google.
        # But if searching Core Identity (Artist/Title), treat as Main Search (Respect Provider).
        is_core_identity = False
        if field_def:
            if field_def.name in ['title', 'performers', 'unified_artist']:
                is_core_identity = True
            else:
                effective_provider = "Google"

        # 2. Resolve Context (Draft Priority > Model Fallback)
        def resolve(field):
            return draft_values.get(field) or getattr(song, field, "")
            
        title = resolve('title')
        
        # Artist Resolution Logic (Business Logic)
        # Try performers -> unified_artist -> artist
        artist = draft_values.get('performers') # Chip tray returns string joined
        if not artist:
            # Fallback to model
            p = getattr(song, 'performers', [])
            if p and isinstance(p, list): 
                artist = p[0] 
            else: 
                artist = getattr(song, 'unified_artist', "") or getattr(song, 'artist', "")
        
        # Micro-button context
        field_value = ""
        field_name = ""
        field_header = ""
        
        if field_def:
            field_name = field_def.name
            field_header = field_def.ui_header
            field_value = resolve(field_name)

        # 3. Construct Query
        # If it's a Core Identity search (Artist/Title button), treat acts as normal `Artist - Title` search
        if is_core_identity:
             # Pass empty field_name to treat it as a generic search (avoiding potential specific field logic)
             query = self.construct_query(effective_provider, title, str(artist), "", "")
        else:
             query = self.construct_query(effective_provider, title, str(artist), str(field_value), field_name)

        # Google Context Enhancement for Non-Core Fields
        if effective_provider == "Google" and field_name and not is_core_identity and field_header:
            query = f"{query} {field_header}"

        return self.get_search_url(effective_provider, query)



