import urllib.parse
from src.models.domain import Song


def _mb_escape(value: str) -> str:
    """Escape characters that would break a Lucene quoted phrase.

    Backslash must be escaped first, then the double quote, so a stray quote
    in a title/performer name doesn't terminate the phrase early.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


class SearchService:
    """
    SearchService generates external search URLs (Spotify, Google) for Song domain models.
    Centralizing this logic on the backend ensures consistency across all consumer frontends.
    """

    ENGINES = {
        "spotify": "Spotify",
        "google": "Google",
        "youtube": "YouTube",
        "musicbrainz": "MusicBrainz",
    }

    def get_search_url(self, song: Song, engine: str = "spotify") -> str:
        """
        Builds a search URL for the given song and engine.
        Spotify typically expects 'Artist Title' or 'ArtistA, ArtistB Title'.
        Google typically includes 'metadata' or 'lyrics' for better relevance.
        """
        # Extract performer names
        performers = [
            c.display_name for c in song.credits if c.role_name == "Performer"
        ]
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
            # Google search
            return f"https://www.google.com/search?q={urllib.parse.quote(base_query)}"

        elif engine.lower() == "youtube":
            # YouTube search
            return f"https://www.youtube.com/results?search_query={urllib.parse.quote(base_query)}"

        elif engine.lower() == "musicbrainz":
            # MusicBrainz advanced (Lucene) search. type=recording targets
            # songs/tracks (type=release would be an album). A flat query
            # matches loosely with an implicit OR across the recording name
            # and floods results, so build a fielded query instead: scope the
            # title to recording:, each performer to artist:, quote them as
            # phrases, and AND them together to narrow the match.
            # method=advanced (not indexed) is what makes MusicBrainz parse the
            # field syntax rather than treat it as literal text.
            # Mirrors the documented example: "voodoo people" AND artist:"the prodigy"
            lucene_parts = [f'recording:"{_mb_escape(title)}"']
            lucene_parts.extend(f'artist:"{_mb_escape(p)}"' for p in performers)
            lucene_query = " AND ".join(lucene_parts)
            return (
                "https://musicbrainz.org/search?"
                f"query={urllib.parse.quote(lucene_query)}"
                "&type=recording&method=advanced"
            )

        else:
            # Fallback to a simple Google search if engine is unknown
            return f"https://www.google.com/search?q={urllib.parse.quote(base_query)}"
