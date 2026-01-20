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

    def get_by_owner(self, identity_id: int) -> List[ArtistName]:
        """Fetch all names owned by an identity."""
        return self._repo.get_by_owner(identity_id)

    def search_names(self, query: str) -> List[ArtistName]:
        """Search for artist names (LIKE match)."""
        return self._repo.search(query)

    def find_exact(self, name: str) -> List[ArtistName]:
        """Find exact name matches (UTF8_NOCASE)."""
        return self._repo.find_exact(name)

    def create_name(self, display_name: str, owner_identity_id: Optional[int] = None, 
                    is_primary: bool = False, batch_id: Optional[str] = None) -> ArtistName:
        """Create a new artist name."""
        name = ArtistName(
            display_name=display_name, 
            owner_identity_id=owner_identity_id, 
            is_primary_name=is_primary
        )
        name_id = self._repo.insert(name, batch_id=batch_id)
        name.name_id = name_id
        return name

    def update_name(self, name: ArtistName, batch_id: Optional[str] = None) -> bool:
        """Update artist name details."""
        return self._repo.update(name, batch_id=batch_id)

    def delete_name(self, name_id: int, batch_id: Optional[str] = None) -> bool:
        """Delete an artist name."""
        return self._repo.delete(name_id, batch_id=batch_id)
