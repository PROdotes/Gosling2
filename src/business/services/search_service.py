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

    def get_search_url(self, provider: str, title: str = "", artist: str = "", field_name: str = "", field_header: str = "") -> str:
        """
        Construct search URL based on provider and context.
        """
        # Clean Inputs for structured providers
        a_clean = urllib.parse.quote(artist.strip()) if artist else ""
        t_clean = urllib.parse.quote(title.strip()) if title else ""
        
        # Generic Query String (Fallback for Google/YouTube)
        # Format: "Artist Title [Field]"
        raw_query_parts = []
        if artist: raw_query_parts.append(artist.strip())
        if title: raw_query_parts.append(title.strip())
        
        # Add Field Context (e.g. "Year", "Composer") if searching a specific field
        # WE DONT DO THIS FOR CORE IDENTITY (Artist/Title buttons)
        is_core = field_name in ['title', 'performers', 'unified_artist', 'artist']
        
        if field_header and not is_core:
             raw_query_parts.append(field_header.strip())
             
        generic_query = " ".join(raw_query_parts).strip()
        q_clean = urllib.parse.quote(generic_query)
        
        # --- PROVIDER LOGIC ---
        
        if provider == "Google":
             return f"https://www.google.com/search?q={q_clean}"
             
        elif provider == "Spotify":
             return f"https://open.spotify.com/search/{q_clean}"
             
        elif provider == "YouTube":
             return f"https://www.youtube.com/results?search_query={q_clean}"
             
        elif provider == "MusicBrainz":
             # User Specific Requirement: Use /taglookup/index endpoint
             # Example: https://musicbrainz.org/taglookup/index?tag-lookup.artist=...&tag-lookup.release=...
             return f"https://musicbrainz.org/taglookup/index?tag-lookup.artist={a_clean}&tag-lookup.release={t_clean}"
             
        elif provider == "Discogs":
             return f"https://www.discogs.com/search/?q={q_clean}&type=release"
             
        elif provider == "ZAMP":
             # ZAMP Logic: Title Only preference
             zamp_q = t_clean if t_clean else q_clean
             return f"https://www.zamp.hr/baza-autora/rezultati-djela/pregled/{zamp_q}"
        
        return ""

    def prepare_search(self, song, draft_values: dict, preferred_provider: str, field_def=None) -> str:
        """
        High-level entry point. 
        Gathers raw data and delegates URL construction.
        """
        # 1. Resolve Effective Provider
        effective_provider = preferred_provider
        field_name = ""
        field_header = ""
        
        if field_def:
            field_name = field_def.name
            field_header = field_def.ui_header
            
            # Logic: If searching specific metadata (Composer, Lyrics, Year), Force Google.
            # But if searching Core Identity (Artist/Title), treat as Main Search (Respect Provider).
            if field_name not in ['title', 'performers', 'unified_artist', 'artist']:
                effective_provider = "Google"

        # 2. Resolve Context (Draft Priority > Model Fallback)
        def resolve(field):
            return draft_values.get(field) or getattr(song, field, "")
            
        title = str(resolve('title'))
        
        # Artist Resolution Logic
        artist = str(draft_values.get('performers') or "")
        if not artist:
            p = getattr(song, 'performers', [])
            if p and isinstance(p, list): 
                artist = p[0] 
            else: 
                artist = getattr(song, 'unified_artist', "") or getattr(song, 'artist', "")
        artist = str(artist)

        # 3. Delegate to centralized URL builder
        return self.get_search_url(
            provider=effective_provider, 
            title=title, 
            artist=artist, 
            field_name=field_name,
            field_header=field_header
        )



