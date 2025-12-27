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

    def get_songs_by_ids(self, song_ids: List[int]) -> List[Song]:
        """Bulk fetch songs by their DB IDs"""
        return self.song_repository.get_songs_by_ids(song_ids)

    def get_songs_by_paths(self, paths: List[str]) -> List[Song]:
        """Bulk fetch songs by their paths"""
        return self.song_repository.get_songs_by_paths(paths)

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

    def assign_album(self, source_id: int, album_title: str, artist: Optional[str] = None, year: Optional[int] = None) -> Album:
        """
        Link a song to an album by title, artist, and year (Find or Create).
        This prevents different artists with the same album title from merging.
        """
        if not album_title or not album_title.strip():
            return None
            
        album, created = self.album_repository.get_or_create(
            title=album_title.strip(),
            album_artist=artist,
            release_year=year
        )

        # Check if already linked? (Repository uses INSERT OR IGNORE, safe to call)
        self.album_repository.add_song_to_album(source_id, album.album_id)
        
        return album

    def get_distinct_filter_values(self, field_name: str) -> List:
        """
        Get distinct values for a filterable field using surgical targeted queries.
        This bypasses massive JOINs to prevent UI freezes at startup.
        """
        from src.core import yellberus
        
        # 1. OPTIMIZED PATH: Direct queries for common fields
        query = None
        if field_name == "recording_year":
            query = "SELECT DISTINCT RecordingYear FROM Songs WHERE RecordingYear IS NOT NULL"
        elif field_name == "performers":
            query = """
                SELECT DISTINCT C.ContributorName 
                FROM Contributors C
                JOIN MediaSourceContributorRoles MSCR ON C.ContributorID = MSCR.ContributorID
                JOIN Roles R ON MSCR.RoleID = R.RoleID
                WHERE R.RoleName = 'Performer'
            """
        elif field_name == "composers":
            query = """
                SELECT DISTINCT C.ContributorName 
                FROM Contributors C
                JOIN MediaSourceContributorRoles MSCR ON C.ContributorID = MSCR.ContributorID
                JOIN Roles R ON MSCR.RoleID = R.RoleID
                WHERE R.RoleName = 'Composer'
            """
        elif field_name == "publisher":
            query = "SELECT DISTINCT PublisherName FROM Publishers"
        elif field_name == "genre":
            query = "SELECT DISTINCT TagName FROM Tags WHERE Category = 'Genre'"
        elif field_name == "album":
            query = "SELECT DISTINCT Title FROM Albums"
        elif field_name == "album_artist":
            query = "SELECT DISTINCT AlbumArtist FROM Albums WHERE AlbumArtist IS NOT NULL"

        if query:
            with self.song_repository.get_connection() as conn:
                cursor = conn.execute(query)
                results = [row[0] for row in cursor.fetchall() if row[0]]
                return sorted(results, key=lambda x: str(x).lower() if isinstance(x, str) else x)

        # 2. FALLBACK PATH: For less common or complex fields
        field_def = yellberus.get_field(field_name)
        if not field_def:
            return []
            
        expr = field_def.query_expression or field_def.db_column
        if " AS " in expr.upper():
            expr = expr.split(" AS ")[0].strip()
            
        query = f"SELECT DISTINCT {expr} {yellberus.QUERY_FROM} {yellberus.QUERY_BASE_WHERE}"
        
        with self.song_repository.get_connection() as conn:
            cursor = conn.execute(query)
            # Use a set to avoid duplicates from comma-splitting
            results = set()
            for row in cursor.fetchall():
                val = row[0]
                if val:
                    if isinstance(val, str) and ',' in val:
                        for item in val.split(','):
                            item = item.strip()
                            if item: results.add(item)
                    else:
                        results.add(val)
            return sorted(list(results), key=lambda x: str(x).lower() if isinstance(x, str) else x)
