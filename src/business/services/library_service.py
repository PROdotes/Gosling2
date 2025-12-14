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

    def get_contributors_by_role(self, role_name: str) -> List[Tuple[int, str]]:
        """Get all contributors for a specific role"""
        return self.contributor_repository.get_by_role(role_name)

    def get_songs_by_performer(self, performer_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific performer"""
        return self.song_repository.get_by_performer(performer_name)

    def get_songs_by_composer(self, composer_name: str) -> Tuple[List[str], List[Tuple]]:
        """Get all songs by a specific composer"""
        return self.song_repository.get_by_composer(composer_name)

    def get_song_by_path(self, path: str) -> Optional[Song]:
        """Get full song object by path"""
        return self.song_repository.get_by_path(path)


