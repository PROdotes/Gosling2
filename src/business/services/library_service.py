"""Library management service"""
from typing import List, Optional, Tuple, Any
from .song_service import SongService
from .contributor_service import ContributorService
from .album_service import AlbumService
from .publisher_service import PublisherService
from .tag_service import TagService
from .search_service import SearchService
from ...data.models.song import Song
from ...data.models.album import Album


class LibraryService:
    """
    Main aggregator service for the music library.
    Coordinates operations across specialized sub-services.
    """

    def __init__(self, song_service: SongService, 
                 contributor_service: ContributorService, 
                 album_service: AlbumService,
                 publisher_service: PublisherService,
                 tag_service: TagService,
                 search_service: SearchService,
                 spotify_parsing_service=None):
        self.song_service = song_service
        self.contributor_service = contributor_service
        self.album_service = album_service
        self.publisher_service = publisher_service
        self.tag_service = tag_service
        self.search_service = search_service
        self.spotify_parsing_service = spotify_parsing_service


    def add_file(self, file_path: str) -> Optional[int]:
        """Add a file to the library (Legacy)"""
        return self.song_service._repo.insert(file_path)

    def add_song(self, song: Song, **kwargs) -> Optional[int]:
        """Add a song with full metadata to the library (Atomic Audit)"""
        return self.song_service._repo.insert(song, **kwargs)

    def get_all_songs(self) -> Tuple[List[str], List[Tuple]]:
        """Get all songs from the library"""
        return self.song_service.get_all()

    def delete_song(self, file_id: int) -> bool:
        """Delete a song from the library"""
        return self.song_service.delete(file_id)

    def update_song(self, song: Song, batch_id: Optional[str] = None, **kwargs) -> bool:
        """Update song metadata."""
        return self.song_service.update(song, batch_id=batch_id, **kwargs)

    def log_action(self, action_type: str, target_table: str = None, target_id: int = None, details: Any = None) -> None:
        """Log a high-level systemic or user action."""
        self.song_service.log_action(action_type, target_table, target_id, details)

    def update_song_status(self, file_id: int, is_done: bool) -> bool:
        """Update song status"""
        return self.song_service.update_status(file_id, is_done)

    def get_contributors_by_role(self, role_name: str) -> List[Any]:
        """Get all contributors for a specific role"""
        return self.contributor_service.get_by_role(role_name)

    def get_songs_by_performer(self, performer_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific performer"""
        return self.song_service._repo.get_by_performer(performer_name)

    def get_songs_by_unified_artist(self, artist_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific artist (T-17: Identity Graph aware)"""
        related_names = self.contributor_service.resolve_identity_graph(artist_name)
        return self.song_service._repo.get_by_unified_artists(related_names)


    def get_songs_by_composer(self, composer_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific composer"""
        return self.song_service._repo.get_by_composer(composer_name)

    def get_song_by_path(self, path: str) -> Optional[Song]:
        """Get full song object by path"""
        return self.song_service.get_by_path(path)

    def get_song_by_id(self, song_id: int) -> Optional[Song]:
        """Get full song object by DB ID"""
        return self.song_service.get_by_id(song_id)

    def get_songs_by_ids(self, song_ids: List[int]) -> List[Song]:
        """Bulk fetch songs by their DB IDs"""
        return self.song_service.get_songs_by_ids(song_ids)

    def get_songs_by_paths(self, paths: List[str]) -> List[Song]:
        """Bulk fetch songs by their paths"""
        return self.song_service._repo.get_songs_by_paths(paths)

    def find_by_isrc(self, isrc: str) -> Optional[Song]:
        """Find a song by ISRC for duplicate detection"""
        return self.song_service._repo.get_by_isrc(isrc)

    def find_by_audio_hash(self, audio_hash: str) -> Optional[Song]:
        """Find a song by audio hash for duplicate detection"""
        return self.song_service._repo.get_by_audio_hash(audio_hash)



    def get_all_aliases(self) -> List[str]:
        """Get all distinct alias names"""
        return self.contributor_service.get_all_aliases()

    def get_songs_by_year(self, year: int) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific year"""
        return self.song_service.repo.get_by_year(year)

    def get_songs_by_status(self, is_done: bool) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by status"""
        return self.song_service.repo.get_by_status(is_done)

    # ==================== ALBUMS (T-06) ====================

    def get_item_albums(self, source_id: int) -> List[Album]:
        """Get albums linked to a source item."""
        return self.album_service.get_albums_for_song(source_id)

    def assign_album(self, source_id: int, album_title: str, artist: Optional[str] = None, year: Optional[int] = None) -> Album:
        """
        Link a song to an album by title, artist, and year (Find or Create).
        """
        if not album_title or not album_title.strip():
            return None
            
        album, created = self.album_service.get_or_create(
            title=album_title.strip(),
            artist=artist,
            year=year
        )

        self.album_service.link_song_to_album(source_id, album.album_id)
        return album

    def get_distinct_filter_values(self, field_name: str) -> List[Any]:
        """Get distinct values for a field to populate filters."""
        return self.song_service.get_distinct_values(field_name)

    # ==================== WORKFLOW (T-89) ====================

    def is_song_unprocessed(self, song_id: int) -> bool:
        """Check if a song has the 'Status:Unprocessed' tag."""
        return self.tag_service.is_unprocessed(song_id)

    def set_song_unprocessed(self, song_id: int, unprocessed: bool) -> bool:
        """Set the 'Status:Unprocessed' state for a song."""
        return self.tag_service.set_unprocessed(song_id, unprocessed)

    def get_virtual_member_count(self, zip_path: str) -> int:
        """Count how many library items belong to this ZIP container."""
        return self.song_service.get_virtual_member_count(zip_path)

    # ==================== ADDITIONAL SERVICE METHODS ====================

    def get_all_years(self) -> List[int]:
        """Get all distinct recording years for filtering."""
        return self.song_service._repo.get_all_years()

    def get_album_by_id(self, album_id: int) -> Optional[Album]:
        """Get an album by its ID."""
        return self.album_service.get_by_id(album_id)

    def get_all_contributor_names(self) -> List[str]:
        """Get all contributor names (primary names + aliases) for filtering."""
        all_names = set()
        # Get primary names
        primary_names = self.contributor_service.get_all_primary_names()
        all_names.update(primary_names)
        # Get aliases
        aliases = self.contributor_service.get_all_aliases()
        all_names.update(aliases)
        return sorted(list(all_names))

    def get_types_for_names(self, names: List[str]) -> dict:
        """Get contributor types (person/group) for a list of names."""
        return self.contributor_service._repo.get_types_for_names(names)


    def get_human_name(self, table_name: str, record_id: int) -> Optional[str]:
        """Resolve a DB ID into a human-readable name for audit logging purposes."""
        if not record_id: return None
        try:
            if table_name == "Contributors":
                c = self.contributor_service.get_by_id(record_id)
                return c.name if c else f"ID:{record_id}"
            if table_name == "Albums":
                a = self.album_service.get_by_id(record_id)
                return a.title if a else f"ID:{record_id}"
            if table_name == "Songs":
                s = self.song_service.get_by_id(record_id)
                return s.name if s else f"ID:{record_id}"
            if table_name == "Publishers":
                p = self.publisher_service.get_by_id(record_id)
                return p.publisher_name if p else f"ID:{record_id}"
            return f"ID:{record_id}"
        except Exception:
            return f"ID:{record_id}"
