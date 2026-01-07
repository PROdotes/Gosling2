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

    def create_identity(self, identity_type: str, legal_name: Optional[str] = None, batch_id: Optional[str] = None) -> Identity:
        """Create a new identity."""
        identity = Identity(identity_type=identity_type, legal_name=legal_name)
        identity_id = self._repo.insert(identity, batch_id=batch_id)
        identity.identity_id = identity_id
        return identity

    def merge(self, source_id: int, target_id: int, batch_id: Optional[str] = None, **kwargs) -> bool:
        """
        Merge source identity into target identity.
        
        Steps:
        1. Re-parent all names from source to target
        2. Transfer group memberships (handle duplicates)
        3. Delete source identity
        """
        from src.core.audit_logger import AuditLogger
        
        # 0. Log action
        with self._repo.get_connection() as conn:
            AuditLogger(conn, batch_id=batch_id).log_action("MERGE", "Identities", source_id, f"Merged into {target_id}")
            
        # 1. Re-parent names
        names = self._name_repo.get_by_owner(source_id)
        for name in names:
            name.owner_identity_id = target_id
            name.is_primary_name = False  # Merged names become aliases
            if not self._name_repo.update(name, batch_id=batch_id):
                return False
        
        # 2. Transfer GroupMemberships BEFORE deleting source
        # This must happen before delete because ON DELETE CASCADE would destroy them
        self._transfer_memberships(source_id, target_id, batch_id=batch_id)
        
        # 3. Delete source identity (now safe - memberships already transferred)
        self._repo.delete(source_id, batch_id=batch_id)
        return True

    def _transfer_memberships(self, source_id: int, target_id: int, batch_id: Optional[str] = None) -> None:
        """
        Transfer group memberships from source identity to target identity.
        
        Handles:
        - Source is a MEMBER: Transfer to target (skip if duplicate)
        - Source is a GROUP: Transfer members to target group (skip duplicates)
        """
        from src.core.audit_logger import AuditLogger
        
        with self._repo.get_connection() as conn:
            cursor = conn.cursor()
            auditor = AuditLogger(conn, batch_id=batch_id)
            
            # A) Source as MEMBER of groups
            cursor.execute("""
                SELECT MembershipID, GroupIdentityID, MemberIdentityID, CreditedAsNameID 
                FROM GroupMemberships 
                WHERE MemberIdentityID = ?
            """, (source_id,))
            source_memberships = cursor.fetchall()
            
            for row in source_memberships:
                membership_id, group_id, old_member_id, credited_as = row[0], row[1], row[2], row[3]
                # Skip if target is already a member of this group
                cursor.execute("""
                    SELECT 1 FROM GroupMemberships 
                    WHERE GroupIdentityID = ? AND MemberIdentityID = ?
                """, (group_id, target_id))
                if cursor.fetchone():
                    continue  # Already a member, skip
                
                # Capture old state for audit
                old_snapshot = {"MembershipID": membership_id, "GroupIdentityID": group_id, 
                               "MemberIdentityID": old_member_id, "CreditedAsNameID": credited_as}
                    
                # Transfer: Update MemberIdentityID
                cursor.execute("""
                    UPDATE GroupMemberships 
                    SET MemberIdentityID = ?
                    WHERE GroupIdentityID = ? AND MemberIdentityID = ?
                """, (target_id, group_id, source_id))
                
                # Audit the update
                new_snapshot = {"MembershipID": membership_id, "GroupIdentityID": group_id, 
                               "MemberIdentityID": target_id, "CreditedAsNameID": credited_as}
                auditor.log_update("GroupMemberships", membership_id, old_snapshot, new_snapshot)
            
            # B) Source as GROUP owner (if source was a group with members)
            cursor.execute("""
                SELECT MembershipID, GroupIdentityID, MemberIdentityID, CreditedAsNameID 
                FROM GroupMemberships 
                WHERE GroupIdentityID = ?
            """, (source_id,))
            source_as_group = cursor.fetchall()
            
            for row in source_as_group:
                membership_id, old_group_id, member_id, credited_as = row[0], row[1], row[2], row[3]
                # Skip if target already has this member
                cursor.execute("""
                    SELECT 1 FROM GroupMemberships 
                    WHERE GroupIdentityID = ? AND MemberIdentityID = ?
                """, (target_id, member_id))
                if cursor.fetchone():
                    continue
                
                # Capture old state for audit
                old_snapshot = {"MembershipID": membership_id, "GroupIdentityID": old_group_id, 
                               "MemberIdentityID": member_id, "CreditedAsNameID": credited_as}
                    
                # Transfer: Update GroupIdentityID
                cursor.execute("""
                    UPDATE GroupMemberships 
                    SET GroupIdentityID = ?
                    WHERE GroupIdentityID = ? AND MemberIdentityID = ?
                """, (target_id, source_id, member_id))
                
                # Audit the update
                new_snapshot = {"MembershipID": membership_id, "GroupIdentityID": target_id, 
                               "MemberIdentityID": member_id, "CreditedAsNameID": credited_as}
                auditor.log_update("GroupMemberships", membership_id, old_snapshot, new_snapshot)

    def link_name_to_identity(self, name_id: int, identity_id: int, batch_id: Optional[str] = None) -> bool:
        """Link an artist name to an identity."""
        name = self._name_repo.get_by_id(name_id)
        if not name:
            return False
        
        # Audit high-level link
        from src.core.audit_logger import AuditLogger
        with self._repo.get_connection() as conn:
            AuditLogger(conn, batch_id=batch_id).log_action("LINK_NAME", "Identities", identity_id, f"Link Name: {name_id}")

        name.owner_identity_id = identity_id
        return self._name_repo.update(name, batch_id=batch_id)

    def promote_alias(self, contributor_id: int, alias_id: int, batch_id: Optional[str] = None, **kwargs) -> bool:
        """
        Promote an artist name to be the primary name for an identity.
        In the new model, 'contributor_id' is interpreted as 'identity_id'.
        """
        from src.core.audit_logger import AuditLogger
        with self._repo.get_connection() as conn:
            AuditLogger(conn, batch_id=batch_id).log_action("PROMOTE_ALIAS", "Identities", contributor_id, f"To: {alias_id}")

        # 1. Clear current primary name for this identity
        current_names = self._name_repo.get_by_owner(contributor_id)
        for n in current_names:
            if n.is_primary_name:
                n.is_primary_name = False
                self._name_repo.update(n, batch_id=batch_id)
        
        # 2. Set new primary name
        name = self._name_repo.get_by_id(alias_id)
        if name:
            name.is_primary_name = True
            name.owner_identity_id = contributor_id # Ensure it's owned by this identity
            return self._name_repo.update(name, batch_id=batch_id)
        return False

    def move_alias(self, alias_name: str, old_owner_id: int, new_owner_id: int, batch_id: Optional[str] = None, **kwargs) -> bool:
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
            return self._name_repo.update(target_name, batch_id=batch_id)
        return False

    def abdicate(self, old_identity_id: int, heir_name_id: int, adopter_identity_id: int, batch_id: Optional[str] = None) -> bool:
        """
        Abdicate an identity: move the current primary name to another identity,
        and promote an heir to become the new primary of the original identity.
        
        Use case: "Freddie Mercury" identity has aliases ["Ziggy", "Brian"].
        User wants to "steal" Freddie as an alias of "David Bowie".
        - Freddie (primary) moves to Bowie's identity as an alias
        - Ziggy (heir) becomes the new primary of the original identity
        
        Args:
            old_identity_id: The identity being abdicated from
            heir_name_id: NameID that will become the new primary
            adopter_identity_id: Identity that will receive the old primary name
            batch_id: Optional transaction ID
        """
        import uuid
        batch_id = batch_id or str(uuid.uuid4())
        
        from src.core.audit_logger import AuditLogger
        with self._repo.get_connection() as conn:
            AuditLogger(conn, batch_id=batch_id).log_action("ABDICATE", "Identities", old_identity_id, f"Heir: {heir_name_id}, Adopter: {adopter_identity_id}")
            
        # 1. Get current primary name
        names = self._name_repo.get_by_owner(old_identity_id)
        current_primary = None
        for n in names:
            if n.is_primary_name:
                current_primary = n
                break
        
        if not current_primary:
            return False
        
        # 2. Validate heir exists and belongs to same identity
        heir = self._name_repo.get_by_id(heir_name_id)
        if not heir or heir.owner_identity_id != old_identity_id:
            return False
        
        # 3. Demote current primary
        current_primary.is_primary_name = False
        if not self._name_repo.update(current_primary, batch_id=batch_id):
            return False
        
        # 4. Promote heir
        heir.is_primary_name = True
        if not self._name_repo.update(heir, batch_id=batch_id):
            return False
        
        # 5. Move old primary to adopter
        current_primary.owner_identity_id = adopter_identity_id
        return self._name_repo.update(current_primary, batch_id=batch_id)

