"""ArtistName Service Module"""
from typing import Optional, List
from ...data.models.artist_name import ArtistName
from ...data.repositories.artist_name_repository import ArtistNameRepository


class ArtistNameService:
    """Service for managing artist names."""

    def __init__(self, repository: Optional[ArtistNameRepository] = None):
        self._repo = repository or ArtistNameRepository()

    def get_name(self, name_id: int) -> Optional[ArtistName]:
        """Fetch artist name by ID."""
        return self._repo.get_by_id(name_id)

    def search_names(self, query: str) -> List[ArtistName]:
        """Search for artist names."""
        return self._repo.search(query)

    def create_name(self, display_name: str, owner_identity_id: Optional[int] = None, 
                    is_primary: bool = False) -> ArtistName:
        """Create a new artist name."""
        name = ArtistName(
            display_name=display_name, 
            owner_identity_id=owner_identity_id, 
            is_primary_name=is_primary
        )
        name_id = self._repo.insert(name)
        name.name_id = name_id
        return name

    def update_name(self, name: ArtistName) -> bool:
        """Update artist name details."""
        return self._repo.update(name)
