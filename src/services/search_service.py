import urllib.parse
from src.models.domain import Song

class SearchService:
    """
    SearchService generates external search URLs (Spotify, Google) for Song domain models.
    Centralizing this logic on the backend ensures consistency across all consumer frontends.
    """

    def get_search_url(self, song: Song, engine: str = "spotify") -> str:
        """
        Builds a search URL for the given song and engine.
        Spotify typically expects 'Artist Title' or 'ArtistA, ArtistB Title'.
        Google typically includes 'metadata' or 'lyrics' for better relevance.
        """
        # Extract performer names
        performers = [c.display_name for c in song.credits if c.role_name == "Performer"]
        performer_str = ", ".join(performers) if performers else ""
        
        # Build query parts
        title = song.title or song.media_name or "Untitled"
        query_parts = []
        if performer_str:
            query_parts.append(performer_str)
        query_parts.append(title)
        
        base_query = " ".join(query_parts).strip()
        
        if engine.lower() == "spotify":
            # Spotify search pattern
            return f"https://open.spotify.com/search/{urllib.parse.quote(base_query)}"
        
        elif engine.lower() == "google":
            # Google search with 'metadata' suffix
            full_query = f"{base_query} metadata"
            return f"https://www.google.com/search?q={urllib.parse.quote(full_query)}"
        
        else:
            # Fallback to a simple Google search if engine is unknown
            return f"https://www.google.com/search?q={urllib.parse.quote(base_query)}"
