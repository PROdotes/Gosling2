"""Library management service"""
from typing import List, Optional, Tuple
from ...data.repositories import SongRepository, ContributorRepository, AlbumRepository
from ...data.models.song import Song
from ...data.models.album import Album


class LibraryService:
    """Service for managing the music library"""

    def __init__(self, song_repository: SongRepository, contributor_repository: ContributorRepository, album_repository: Optional[AlbumRepository] = None):
        self.song_repository = song_repository
        self.contributor_repository = contributor_repository
        # Optional for now to avoid breaking existing instantiations not yet updated, 
        # but internal logic will assume it exists if needed.
        self.album_repository = album_repository or AlbumRepository()

    @property
    def album_repo(self):
        """Bridge accessor for UI components expecting 'album_repo'"""
        return self.album_repository

    def add_file(self, file_path: str) -> Optional[int]:
        """Add a file to the library"""
        return self.song_repository.insert(file_path)

    def get_all_songs(self) -> Tuple[List[str], List[Tuple]]:
        """Get all songs from the library"""
        return self.song_repository.get_all()

    def delete_song(self, file_id: int) -> bool:
        """Delete a song from the library"""
        return self.song_repository.delete(file_id)

    def update_song(self, song: Song) -> bool:
        """Update song metadata"""
        return self.song_repository.update(song)

    def update_song_status(self, file_id: int, is_done: bool) -> bool:
        """Update song status"""
        return self.song_repository.update_status(file_id, is_done)

    def get_contributors_by_role(self, role_name: str) -> List[Tuple[int, str]]:
        """Get all contributors for a specific role"""
        return self.contributor_repository.get_by_role(role_name)

    def get_songs_by_performer(self, performer_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific performer"""
        return self.song_repository.get_by_performer(performer_name)

    def get_songs_by_unified_artist(self, artist_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific artist (T-17: Identity Graph aware)"""
        # Resolve Bob -> [Robert, The Bobs, etc.]
        related_names = self.contributor_repository.resolve_identity_graph(artist_name)
        return self.song_repository.get_by_unified_artists(related_names)

    def get_songs_by_composer(self, composer_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific composer"""
        return self.song_repository.get_by_composer(composer_name)

    def get_song_by_path(self, path: str) -> Optional[Song]:
        """Get full song object by path"""
        return self.song_repository.get_by_path(path)

    def get_song_by_id(self, song_id: int) -> Optional[Song]:
        """Get full song object by DB ID"""
        return self.song_repository.get_by_id(song_id)

    def find_by_isrc(self, isrc: str) -> Optional[Song]:
        """Find a song by ISRC for duplicate detection"""
        return self.song_repository.get_by_isrc(isrc)

    def find_by_audio_hash(self, audio_hash: str) -> Optional[Song]:
        """Find a song by audio hash for duplicate detection"""
        return self.song_repository.get_by_audio_hash(audio_hash)



    def get_all_years(self) -> List[int]:
        """Get all distinct recording years"""
        return self.song_repository.get_all_years()

    # get_all_groups removed (redundant/0-result risk)

    def get_all_aliases(self) -> List[str]:
        """Get all distinct alias names"""
        return self.contributor_repository.get_all_aliases()

    def get_songs_by_year(self, year: int) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific year"""
        return self.song_repository.get_by_year(year)

    def get_songs_by_status(self, is_done: bool) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by status"""
        return self.song_repository.get_by_status(is_done)

    # ==================== ALBUMS (T-06) ====================

    def get_item_albums(self, source_id: int) -> List[Album]:
        """Get albums linked to a source item."""
        return self.album_repository.get_albums_for_song(source_id)

    def assign_album(self, source_id: int, album_title: str) -> Album:
        """
        Link a song to an album by title (Find or Create).
        If the song is already linked to this album, does nothing.
        """
        if not album_title or not album_title.strip():
            return None
            
        album, created = self.album_repository.get_or_create(album_title.strip())
        
        # Check if already linked? (Repository uses INSERT OR IGNORE, safe to call)
        self.album_repository.add_song_to_album(source_id, album.album_id)
        
        return album

    def get_distinct_filter_values(self, field_expression: str) -> List:
        """
        Get distinct values for a filterable field using dynamic SQL.
        Uses Yellberus QUERY_FROM for the FROM clause.
        
        Args:
            field_expression: The SQL expression or column name (e.g., "S.RecordingYear" or "GROUP_CONCAT(...)")
        
        Returns:
            List of unique values for that field.
        """
        from src.core import yellberus
        
        # Strip "AS Alias" if present in query_expression
        expr = field_expression
        if " AS " in expr.upper():
            expr = expr.split(" AS ")[0].strip()
        
        query = f"""
            SELECT DISTINCT {expr}
            {yellberus.QUERY_FROM}
            {yellberus.QUERY_BASE_WHERE}
        """
        
        with self.song_repository.get_connection() as conn:
            cursor = conn.execute(query)
            results = []
            for row in cursor.fetchall():
                val = row[0]
                if val is not None and str(val).strip():
                    # Handle comma-separated lists (from GROUP_CONCAT)
                    if ',' in str(val):
                        for item in str(val).split(','):
                            item = item.strip()
                            if item and item not in results:
                                results.append(item)
                    else:
                        if val not in results:
                            results.append(val)
            return sorted(results, key=lambda x: str(x).lower() if isinstance(x, str) else x)
