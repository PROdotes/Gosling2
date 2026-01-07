"""
Contributor Service

Handles business logic for Contributors (Artists, Musicians, Composers).
"""
from typing import List, Optional, Tuple
from ...data.models.contributor import Contributor
from ...data.repositories.contributor_repository import ContributorRepository

class ContributorService:
    """Service for managing contributor identities and their metadata."""
    
    def __init__(self, contributor_repository: Optional[ContributorRepository] = None):
        self._repo = contributor_repository or ContributorRepository()

    def get_all(self) -> List[Contributor]:
        """Fetch all contributors."""
        return self._repo.get_all()

    def search(self, query: str) -> List[Contributor]:
        """Search for contributors by name or alias."""
        return self._repo.search(query)

    def get_all_by_type(self, type_name: str) -> List[Contributor]:
        """Fetch all contributors of a specific type (Person, Group, Alias)."""
        return self._repo.get_all_by_type(type_name)

    def search_identities(self, query: str) -> List[Tuple[int, str, str, str]]:
        """Search for ANY matching name (Primary or Alias) and return flat results."""
        return self._repo.search_identities(query)

    def get_by_id(self, contributor_id: int) -> Optional[Contributor]:
        """Fetch a specific contributor by its ID."""
        return self._repo.get_by_id(contributor_id)

    def get_by_name(self, name: str) -> Optional[Contributor]:
        """Fetch a specific contributor by its primary name or alias."""
        return self._repo.get_by_name(name)

    def get_or_create(self, name: str, type: str = 'person') -> Tuple[Contributor, bool]:
        """Find an existing contributor or create a new one."""
        return self._repo.get_or_create(name, type)

    def update(self, contributor: Contributor) -> bool:
        """Update an existing contributor record."""
        return self._repo.update(contributor)

    def delete(self, contributor_id: int) -> bool:
        """Delete a contributor record."""
        return self._repo.delete(contributor_id)

    def get_usage_count(self, contributor_id: int) -> int:
        """Count how many songs/albums a contributor is linked to."""
        return self._repo.get_usage_count(contributor_id)

    def resolve_identity_graph(self, search_term: str) -> List[str]:
        """
        Expand a search term to include all related identities (aliases, group members).
        This is the core of the 'T-17 Identity Graph' aware search.
        """
        return self._repo.resolve_identity_graph(search_term)

    def get_members(self, group_id: int) -> List[Contributor]:
        """Get all members of a specific Group."""
        return self._repo.get_members(group_id)

    def merge_contributors(self, source_id: int, target_id: int, create_alias: bool = True) -> bool:
        """Merge one contributor identity into another."""
        return self._repo.merge(source_id, target_id, create_alias)

    def get_by_role(self, role_name: str) -> List[Tuple[int, str]]:
        """Get all contributors for a specific role."""
        return self._repo.get_by_role(role_name)

    def get_all_aliases(self) -> List[str]:
        """Get all distinct alias names."""
        return self._repo.get_all_aliases()

    def get_member_count(self, contributor_id: int) -> int:
        """Get count of members in a group."""
        return self._repo.get_member_count(contributor_id)

    def get_aliases(self, contributor_id: int) -> List[Tuple[int, str]]:
        """Get aliases for a contributor."""
        return self._repo.get_aliases(contributor_id)

    def get_groups(self, contributor_id: int) -> List[Tuple[int, str]]:
        """Get groups this contributor belongs to."""
        return self._repo.get_groups(contributor_id)

    def validate_identity(self, name: str, exclude_id: Optional[int] = None) -> Tuple[Optional[int], Optional[str]]:
        """Check if name conflicts with existing identity."""
        return self._repo.validate_identity(name, exclude_id)

    def add_song_role(self, source_id: int, contributor_id: int, role_name: str, batch_id: Optional[str] = None) -> bool:
        """Instant Link: Link a contributor to a song with a specific role."""
        return self._repo.add_song_role(source_id, contributor_id, role_name, batch_id=batch_id)

    def remove_song_role(self, source_id: int, contributor_id: int, role_name: str, batch_id: Optional[str] = None) -> bool:
        """Instant Unlink: Remove a contributor role from a song."""
        return self._repo.remove_song_role(source_id, contributor_id, role_name, batch_id=batch_id)

    def create(self, name: str, type: str = 'person', batch_id: Optional[str] = None) -> Contributor:
        """Create new contributor."""
        return self._repo.create(name, type, batch_id=batch_id)

    def merge(self, source_id: int, target_id: int, create_alias: bool = True, batch_id: Optional[str] = None) -> bool:
        """Merge contributor source_id into target_id."""
        return self._repo.merge(source_id, target_id, create_alias, batch_id=batch_id)

    def add_alias(self, contributor_id: int, alias_name: str, batch_id: Optional[str] = None) -> Optional[int]:
        """Add an alias to a contributor."""
        return self._repo.add_alias(contributor_id, alias_name, batch_id=batch_id)

    def delete_alias(self, alias_id: int, batch_id: Optional[str] = None) -> bool:
        """Delete an alias."""
        return self._repo.delete_alias(alias_id, batch_id=batch_id)

    def promote_alias(self, contributor_id: int, alias_id: int, batch_id: Optional[str] = None) -> bool:
        """Promote an alias to primary name."""
        return self._repo.promote_alias(contributor_id, alias_id, batch_id=batch_id)

    def update_alias(self, alias_id: int, new_name: str, batch_id: Optional[str] = None) -> bool:
        """Update an alias name."""
        return self._repo.update_alias(alias_id, new_name, batch_id=batch_id)

    def move_alias(self, alias_name: str, old_owner_id: int, new_owner_id: int, batch_id: Optional[str] = None) -> bool:
        """Transfer Alias ownership."""
        return self._repo.move_alias(alias_name, old_owner_id, new_owner_id, batch_id=batch_id)

    def abdicate_identity(self, current_id: int, heir_alias_id: int, target_parent_id: int, batch_id: Optional[str] = None) -> bool:
        """Abdicate an identity, transferring its primary name to an alias of another identity."""
        return self._repo.abdicate_identity(current_id, heir_alias_id, target_parent_id, batch_id=batch_id)

    def add_member(self, group_id: int, member_id: int, member_alias_id: Optional[int] = None, batch_id: Optional[str] = None) -> bool:
        """Add a member to a group."""
        return self._repo.add_member(group_id, member_id, member_alias_id=member_alias_id, batch_id=batch_id)

    def remove_member(self, group_id: int, member_id: int, batch_id: Optional[str] = None) -> bool:
        """Remove a member from a group."""
        return self._repo.remove_member(group_id, member_id, batch_id=batch_id)

    def swap_song_contributor(self, source_id: int, old_contrib_id: int, new_contrib_id: int, batch_id: Optional[str] = None) -> bool:
        """Swap contributor on a specific song (Fix This Song Only)."""
        return self._repo.swap_song_contributor(source_id, old_contrib_id, new_contrib_id, batch_id=batch_id)
