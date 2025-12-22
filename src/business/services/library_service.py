"""Library management service"""
from typing import List, Optional, Tuple
from ...data.repositories import SongRepository, ContributorRepository
from ...data.models.song import Song


class LibraryService:
    """Service for managing the music library"""

    def __init__(self, song_repository: SongRepository, contributor_repository: ContributorRepository):
        self.song_repository = song_repository
        self.contributor_repository = contributor_repository

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
