"""
Contributor Service

Handles business logic for Contributors (Artists, Musicians, Composers).
"""
from typing import List, Optional, Tuple
from ...data.models.contributor import Contributor
from ...data.repositories.contributor_repository import ContributorRepository

class ContributorService:
    """
    Service for managing contributor identities and their metadata.
    Refactored to act as a facade for the new Identity and ArtistName services.
    """
    
    def __init__(self, contributor_repository: Optional[ContributorRepository] = None):
        # Keep old repo for legacy fallback if needed, but primary logic uses new services
        self._repo = contributor_repository or ContributorRepository()
        from .identity_service import IdentityService
        from .artist_name_service import ArtistNameService
        from ..repositories.credit_repository import CreditRepository
        self._identity_service = IdentityService()
        self._name_service = ArtistNameService()
        self._credit_repo = CreditRepository()

    def get_all(self) -> List[Contributor]:
        """Fetch all contributors (Mapped to all ArtistNames)."""
        # This is expensive in new model, ideally we should limit or use a view
        return self._repo.get_all()

    def search(self, query: str) -> List[Contributor]:
        """Search for contributors by name or alias."""
        names = self._name_service.search_names(query)
        return [
            Contributor(
                contributor_id=n.name_id,
                name=n.display_name,
                sort_name=n.sort_name
            ) for n in names
        ]

    def get_by_id(self, contributor_id: int) -> Optional[Contributor]:
        """Fetch a specific contributor by its ID. (Maps to ArtistName)"""
        name = self._name_service.get_name(contributor_id)
        if not name:
            return None
        return Contributor(
            contributor_id=name.name_id,
            name=name.display_name,
            sort_name=name.sort_name
        )

    def get_by_name(self, name: str) -> Optional[Contributor]:
        """Fetch a specific contributor by its primary name or alias."""
        names = self._name_service.search_names(name)
        if not names:
            return None
        # Try to find exact match
        for n in names:
            if n.display_name.lower() == name.lower():
                return Contributor(
                    contributor_id=n.name_id,
                    name=n.display_name,
                    sort_name=n.sort_name
                )
        return None

    def create(self, name: str, type: str = 'person', batch_id: Optional[str] = None) -> Contributor:
        """Create new contributor (Identity + Primary ArtistName)."""
        identity = self._identity_service.create_identity(type, legal_name=name)
        artist_name = self._name_service.create_name(name, owner_identity_id=identity.identity_id, is_primary=True)
        return Contributor(
            contributor_id=artist_name.name_id,
            name=artist_name.display_name,
            sort_name=artist_name.sort_name,
            type=type
        )

    def merge(self, source_id: int, target_id: int, create_alias: bool = True, batch_id: Optional[str] = None) -> bool:
        """Merge contributor source_id into target_id (Identity Merge)."""
        # In new model, source_id and target_id are NameIDs. 
        # We need to find their identities and merge them.
        s_name = self._name_service.get_name(source_id)
        t_name = self._name_service.get_name(target_id)
        
        if not s_name or not t_name:
            return False
        
        if not s_name.owner_identity_id or not t_name.owner_identity_id:
            # Orphan merge: just link source name to target identity
            if not t_name.owner_identity_id:
                return False # Cannot merge into an orphan target identity-wise
            s_name.owner_identity_id = t_name.owner_identity_id
            return self._name_service.update_name(s_name)
            
        return self._identity_service.merge(s_name.owner_identity_id, t_name.owner_identity_id)

    def add_song_role(self, source_id: int, contributor_id: int, role_name: str, batch_id: Optional[str] = None) -> bool:
        """Link a contributor (NameID) to a song with a specific role."""
        # Get RoleID
        from src.data.database import Database
        with Database().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = ?", (role_name,))
            row = cursor.fetchone()
            if not row: return False
            role_id = row[0]
            
        return bool(self._credit_repo.add_song_credit(source_id, contributor_id, role_id))

    def remove_song_role(self, source_id: int, contributor_id: int, role_name: str, batch_id: Optional[str] = None) -> bool:
        """Remove a contributor role from a song."""
        from src.data.database import Database
        with Database().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = ?", (role_name,))
            row = cursor.fetchone()
            if not row: return False
            role_id = row[0]
            
        return self._credit_repo.remove_song_credit(source_id, contributor_id, role_id)

    def delete(self, contributor_id: int) -> bool:
        """Delete a contributor record (ArtistName)."""
        # Note: This doesn't delete the identity, just the name.
        # This matches the 'NameID as ContributorID' mapping.
        from ...data.repositories.artist_name_repository import ArtistNameRepository
        return ArtistNameRepository().delete(contributor_id)

    def get_usage_count(self, contributor_id: int) -> int:
        """Count how many songs/albums a contributor is linked to."""
        from src.data.database import Database
        with Database().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM SongCredits WHERE CreditedNameID = ?", (contributor_id,))
            song_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM AlbumCredits WHERE CreditedNameID = ?", (contributor_id,))
            album_count = cursor.fetchone()[0]
            return song_count + album_count

    def update(self, contributor: Contributor) -> bool:
        """Update an existing contributor record (ArtistName)."""
        name = self._name_service.get_name(contributor.contributor_id)
        if not name: return False
        name.display_name = contributor.name
        name.sort_name = contributor.sort_name
        return self._name_service.update_name(name)
