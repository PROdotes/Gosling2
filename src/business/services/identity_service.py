"""Identity Service Module"""
from typing import Optional, List, Any, Tuple
from ...data.models.identity import Identity
from ...data.repositories.identity_repository import IdentityRepository
from ...data.repositories.artist_name_repository import ArtistNameRepository


class IdentityService:
    """Service for managing real person/group identities and their names."""

    def __init__(self, identity_repository: Optional[IdentityRepository] = None, 
                 name_repository: Optional[ArtistNameRepository] = None):
        self._repo = identity_repository or IdentityRepository()
        self._name_repo = name_repository or ArtistNameRepository()

    def get_identity(self, identity_id: int) -> Optional[Identity]:
        """Fetch identity by ID."""
        return self._repo.get_by_id(identity_id)

    def create_identity(self, identity_type: str, legal_name: Optional[str] = None) -> Identity:
        """Create a new identity."""
        identity = Identity(identity_type=identity_type, legal_name=legal_name)
        identity_id = self._repo.insert(identity)
        identity.identity_id = identity_id
        return identity

    def merge(self, source_id: int, target_id: int, **kwargs) -> bool:
        """
        Merge source identity into target identity.
        In the new model, this simply re-parents all names owned by source to target.
        """
        names = self._name_repo.get_by_owner(source_id)
        
        success = True
        for name in names:
            name.owner_identity_id = target_id
            if not self._name_repo.update(name):
                success = False
        
        if success:
            # Transfer other identity metadata if necessary (not implemented for now)
            self._repo.delete(source_id)
            
        return success

    def link_name_to_identity(self, name_id: int, identity_id: int) -> bool:
        """Link an artist name to an identity."""
        name = self._name_repo.get_by_id(name_id)
        if not name:
            return False
        
        name.owner_identity_id = identity_id
        return self._name_repo.update(name)

    def promote_alias(self, contributor_id: int, alias_id: int, **kwargs) -> bool:
        """
        Promote an artist name to be the primary name for an identity.
        In the new model, 'contributor_id' is interpreted as 'identity_id'.
        """
        # 1. Clear current primary name for this identity
        current_names = self._name_repo.get_by_owner(contributor_id)
        for n in current_names:
            if n.is_primary_name:
                n.is_primary_name = False
                self._name_repo.update(n)
        
        # 2. Set new primary name
        name = self._name_repo.get_by_id(alias_id)
        if name:
            name.is_primary_name = True
            name.owner_identity_id = contributor_id # Ensure it's owned by this identity
            return self._name_repo.update(name)
        return False

    def move_alias(self, alias_name: str, old_owner_id: int, new_owner_id: int, **kwargs) -> bool:
        """Transfer name ownership from one identity to another."""
        # Find the name by display name and owner
        names = self._name_repo.get_by_owner(old_owner_id)
        target_name = None
        for n in names:
            if n.display_name.lower() == alias_name.lower():
                target_name = n
                break
        
        if target_name:
            target_name.owner_identity_id = new_owner_id
            target_name.is_primary_name = False # Moving names shouldn't automatically make them primary
            return self._name_repo.update(target_name)
        return False
