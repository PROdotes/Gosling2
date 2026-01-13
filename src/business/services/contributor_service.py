"""
Contributor Service

Handles business logic for Contributors (Artists, Musicians, Composers).
"""
from typing import List, Optional, Tuple, Any
from ...data.models.contributor import Contributor
from ...data.repositories.contributor_repository import ContributorRepository

class ContributorService:
    """
    Service for managing contributor identities and their metadata.
    """
    
    def __init__(self, contributor_repository: Optional[ContributorRepository] = None, credit_repository: Optional[any] = None, db_path: Optional[str] = None):
        # Keep old repo for legacy fallback if needed, but primary logic uses new services
        self._db_path = db_path
        self._repo = contributor_repository or ContributorRepository(db_path=db_path)
        
        from .identity_service import IdentityService
        from .artist_name_service import ArtistNameService
        from ...data.repositories.credit_repository import CreditRepository
        from ...data.repositories.identity_repository import IdentityRepository
        from ...data.repositories.artist_name_repository import ArtistNameRepository
        
        # Inject repositories to services to ensure they use the same DB
        self._identity_service = IdentityService(
            identity_repository=IdentityRepository(db_path=db_path),
            name_repository=ArtistNameRepository(db_path=db_path)
        )
        self._name_service = ArtistNameService(
            repository=ArtistNameRepository(db_path=db_path)
        )
        self._credit_repo = credit_repository or CreditRepository(db_path=db_path)

    def get_all(self) -> List[Contributor]:
        """Fetch all contributors (Mapped to all ArtistNames)."""
        with self._credit_repo.get_connection() as conn:
            cursor = conn.cursor()
            # Join ArtistNames and Identities
            cursor.execute("""
                SELECT an.NameID, an.DisplayName, an.SortName, i.IdentityType
                FROM ArtistNames an
                LEFT JOIN Identities i ON an.OwnerIdentityID = i.IdentityID
                WHERE an.IsPrimaryName = 1
                ORDER BY an.SortName
            """)
            return [
                Contributor(
                    contributor_id=row[0],
                    name=row[1],
                    sort_name=row[2], 
                    type=row[3] or 'person'
                ) for row in cursor.fetchall()
            ]


    def get_by_id(self, contributor_id: int) -> Optional[Contributor]:
        """Fetch a specific contributor by its ID. (Maps to ArtistName)"""
        name = self._name_service.get_name(contributor_id)
        if not name:
            return None
            
        c_type = 'person'
        if name.owner_identity_id:
            ident = self._identity_service.get_identity(name.owner_identity_id)
            if ident: c_type = ident.identity_type
            
        return Contributor(
            contributor_id=name.name_id,
            name=name.display_name,
            sort_name=name.sort_name,
            type=c_type
        )

    def get_by_name(self, name: str) -> Optional[Contributor]:
        """Fetch a specific contributor by its primary name or alias."""
        names = self._name_service.search_names(name)
        if not names:
            return None
        # Try to find exact match
        for n in names:
            if n.display_name.lower() == name.lower():
                c_type = 'person'
                if n.owner_identity_id:
                    ident = self._identity_service.get_identity(n.owner_identity_id)
                    if ident: c_type = ident.identity_type
                    
                return Contributor(
                    contributor_id=n.name_id,
                    name=n.display_name,
                    sort_name=n.sort_name,
                    type=c_type
                )
        return None

    def validate_identity(self, name: str, exclude_id: Optional[int] = None) -> Tuple[Optional[int], Optional[str]]:
        """Check if a name already exists and return conflict info (ID, Message)."""
        existing = self.get_by_name(name)
        if existing and existing.contributor_id != exclude_id:
            return existing.contributor_id, f"Artist '{name}' already exists as a {existing.type}."
        return None, None

    def create(self, name: str, type: Optional[str] = 'person', batch_id: Optional[str] = None) -> Contributor:
        """Create new contributor (Identity + Primary ArtistName)."""
        type_lower = (type or 'person').lower()
        identity = self._identity_service.create_identity(type_lower, legal_name=name)
        artist_name = self._name_service.create_name(name, owner_identity_id=identity.identity_id, is_primary=True)
        return Contributor(
            contributor_id=artist_name.name_id,
            name=artist_name.display_name,
            sort_name=artist_name.sort_name,
            type=type_lower
        )

    def get_or_create(self, name: str, type: Optional[str] = 'person') -> Tuple[Contributor, bool]:
        """Get existing contributor or create a new one. Enforces strict name uniqueness."""
        type_lower = (type or 'person').lower()
        
        # 1. Search for name (Case Insensitive / LIKE)
        matches = self.search(name)
        
        # 2. Try to find exact type match first (Best match)
        for m in matches:
            if m.name.lower() == name.lower() and m.type.lower() == type_lower:
                return m, False
                
        # 3. T-Fix: Even if type differs, if the name matches exactly, reuse it.
        # This prevents the "4 Queens" issue where Queen (Artist) and Queen (Composer) 
        # end up as separate records due to minor type or role discrepancies.
        for m in matches:
            if m.name.lower() == name.lower():
                return m, False
                
        # 4. Truly new name, create it
        return self.create(name, type_lower), True

    def merge(self, source_id: int, target_id: int, create_alias: bool = True, batch_id: Optional[str] = None) -> bool:
        """Merge contributor source_id into target_id (Identity Merge)."""
        import uuid
        batch_id = batch_id or str(uuid.uuid4())
        
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
            return self._name_service.update_name(s_name, batch_id=batch_id)
            
        return self._identity_service.merge(s_name.owner_identity_id, t_name.owner_identity_id, batch_id=batch_id)

    def get_by_role(self, role_name: str) -> List[Contributor]:
        """Fetch all contributors who have a specific role assigned at least once."""
        with self._credit_repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT an.NameID, an.DisplayName, an.SortName, i.IdentityType
                FROM ArtistNames an
                JOIN SongCredits sc ON an.NameID = sc.CreditedNameID
                JOIN Roles r ON sc.RoleID = r.RoleID
                LEFT JOIN Identities i ON an.OwnerIdentityID = i.IdentityID
                WHERE r.RoleName = ?
                ORDER BY an.SortName ASC
            """, (role_name,))
            
            return [
                Contributor(
                    contributor_id=row[0],
                    name=row[1],
                    sort_name=row[2],
                    type=row[3] or 'person'
                ) for row in cursor.fetchall()
            ]

    def add_song_role(self, source_id: int, contributor_id: int, role_name: str, batch_id: Optional[str] = None) -> bool:
        """Link a contributor (NameID) to a song with a specific role."""
        # Get RoleID
        with self._credit_repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = ?", (role_name,))
            row = cursor.fetchone()
            if not row: return False
            role_id = row[0]
            
        return bool(self._credit_repo.add_song_credit(source_id, contributor_id, role_id))

    def remove_song_role(self, source_id: int, contributor_id: int, role_name: str, batch_id: Optional[str] = None) -> bool:
        """Remove a contributor role from a song."""
        with self._credit_repo.get_connection() as conn:
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
        with self._credit_repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM SongCredits WHERE CreditedNameID = ?", (contributor_id,))
            song_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM AlbumCredits WHERE CreditedNameID = ?", (contributor_id,))
            album_count = cursor.fetchone()[0]
            return song_count + album_count

    def get_all_aliases(self) -> List[str]:
        """Get all alias names (Non-primary names)."""
        with self._credit_repo.get_connection() as conn:
             cursor = conn.cursor()
             # In new model, aliases are non-primary names
             cursor.execute("SELECT DisplayName FROM ArtistNames WHERE IsPrimaryName = 0 ORDER BY DisplayName ASC")
             return [row[0] for row in cursor.fetchall()]

    def get_all_primary_names(self) -> List[str]:
        """Get all primary artist names."""
        with self._credit_repo.get_connection() as conn:
             cursor = conn.cursor()
             cursor.execute("SELECT DisplayName FROM ArtistNames WHERE IsPrimaryName = 1 ORDER BY DisplayName ASC")
             return [row[0] for row in cursor.fetchall()]

    def resolve_identity_graph(self, search_term: str) -> List[str]:
        """
        Resolve a search term to a complete list of related artist names (Identity Graph).
        Finds the Identity for the term, and returns ALL names associated with that identity (and groups if person).
        """
        if not search_term: return []
        resolved_names = set()
        resolved_names.add(search_term) # Always include original
        
        with self._credit_repo.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Find Identity IDs matching the Name (Fuzzy Match)
            # This allows searching "Farrokh" to find "Farrokh Bulsara" -> Identity -> "Freddie Mercury"
            term_wild = f"%{search_term}%"
            cursor.execute("SELECT OwnerIdentityID FROM ArtistNames WHERE DisplayName LIKE ? COLLATE UTF8_NOCASE", (term_wild,))
            identity_ids = {row[0] for row in cursor.fetchall() if row[0] is not None}
            
            if not identity_ids:
                return list(resolved_names)
            
            # 2. Expand Identity IDs (Person -> Groups)
            # Find groups where these identities are members
            placeholders = ','.join('?' for _ in identity_ids)
            params = list(identity_ids)
            cursor.execute(f"SELECT GroupIdentityID FROM GroupMemberships WHERE MemberIdentityID IN ({placeholders})", params)
            for row in cursor.fetchall():
                identity_ids.add(row[0])
            
            # 3. Get ALL names for these identities
            placeholders = ','.join('?' for _ in identity_ids)
            params = list(identity_ids)
            # Need to execute again with potentially larger set
            cursor.execute(f"SELECT DisplayName FROM ArtistNames WHERE OwnerIdentityID IN ({placeholders})", params)
            for row in cursor.fetchall():
                resolved_names.add(row[0])
                
        return list(resolved_names)

    def update(self, contributor: Contributor) -> bool:
        """
        Smart Update: Updates name/type, or merges if the new name already exists.
        This enforces strict identity uniqueness at the service level.
        """
        name_rec = self._name_service.get_name(contributor.contributor_id)
        if not name_rec: 
            return False
        
        new_name = contributor.name.strip()
        
        # 1. Handle Name Change & Possible Merge
        # Check if ANOTHER contributor already has this name (case-insensitive)
        with self._repo.get_connection() as conn:
            query = "SELECT NameID FROM ArtistNames WHERE DisplayName = ? COLLATE UTF8_NOCASE AND NameID != ?"
            cursor = conn.execute(query, (new_name, contributor.contributor_id))
            collision = cursor.fetchone()
            
        if collision:
            # COLLISION: Merge our current record INTO the existing one
            return self.merge(source_id=contributor.contributor_id, target_id=collision[0])

        # 2. No collision: Perform physical update
        name_rec.display_name = new_name
        name_rec.sort_name = contributor.sort_name
        success = self._name_service.update_name(name_rec)
        
        # 3. Update Identity Type
        if success and name_rec.owner_identity_id:
            identity = self._identity_service.get_identity(name_rec.owner_identity_id)
            if identity and identity.identity_type != contributor.type:
                identity.identity_type = contributor.type.lower()
                from src.data.repositories.identity_repository import IdentityRepository
                IdentityRepository(db_path=self._db_path).update(identity)
                
        return success

    def merge_contributors(self, source_id: int, target_id: int, create_alias: bool = True, batch_id: Optional[str] = None) -> bool:
        """Merge contributor source_id into target_id (Identity Merge). Alias for merge."""
        return self.merge(source_id, target_id, create_alias=create_alias, batch_id=batch_id)

    def merge(self, source_id: int, target_id: int, create_alias: bool = True, batch_id: Optional[str] = None) -> bool:
        """Merge contributor source_id into target_id (Identity Merge)."""
        import uuid
        batch_id = batch_id or str(uuid.uuid4())
        
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
            return self._name_service.update_name(s_name, batch_id=batch_id)
            
        # T-Fix: If they share the SAME identity, we are merging duplicate NAME entries for that identity
        if s_name.owner_identity_id == t_name.owner_identity_id:
            return self._name_repo.merge(source_id, target_id)
            
        # Different identities: Perform deep identity merge
        return self._identity_service.merge(s_name.owner_identity_id, t_name.owner_identity_id, batch_id=batch_id)
        
    # ==========================
    # Group & Alias Management
    # ==========================

    def _get_identity_id(self, name_id: int) -> Optional[int]:
        """Helper: Resolve NameID to OwnerIdentityID."""
        name = self._name_service.get_name(name_id)
        return name.owner_identity_id if name else None

    def get_members(self, group_id: int) -> List[Contributor]:
        """Get members of a group (NameID -> Identity -> Members -> PrimaryNames)."""
        group_identity_id = self._get_identity_id(group_id)
        if not group_identity_id: return []

        with self._credit_repo.get_connection() as conn:
            cursor = conn.cursor()
            # Join GroupMemberships -> Identity -> ArtistNames (Primary)
            # LEFT JOIN to get Alias Name if CreditedAsNameID is set
            query = """
                SELECT 
                    COALESCE(alias.NameID, an.NameID), 
                    COALESCE(alias.DisplayName, an.DisplayName), 
                    COALESCE(alias.SortName, an.SortName), 
                    i.IdentityType,
                    alias.DisplayName
                FROM GroupMemberships gm
                JOIN Identities i ON gm.MemberIdentityID = i.IdentityID
                JOIN ArtistNames an ON i.IdentityID = an.OwnerIdentityID AND an.IsPrimaryName = 1
                LEFT JOIN ArtistNames alias ON gm.CreditedAsNameID = alias.NameID
                WHERE gm.GroupIdentityID = ?
                ORDER BY COALESCE(alias.SortName, an.SortName)
            """
            cursor.execute(query, (group_identity_id,))
            return [
                 Contributor(
                    contributor_id=row[0],
                    name=row[1],
                    sort_name=row[2],
                    type=row[3] or 'person',
                    matched_alias=row[4]
                ) for row in cursor.fetchall()
            ]

    def get_all_by_type(self, type_name: str) -> List[Contributor]:
        """Fetch all contributors of a primary identity type (person, group), including aliases."""
        if not type_name:
            return self.get_all()
            
        type_lower = type_name.lower()
        with self._credit_repo.get_connection() as conn:
            cursor = conn.cursor()
            # T-Fix: Include both Primary and Alias names (IsPrimaryName 1 or 0) 
            # as long as they belong to the correct Identity type.
            cursor.execute("""
                SELECT an.NameID, an.DisplayName, an.SortName, i.IdentityType, an.IsPrimaryName
                FROM ArtistNames an
                JOIN Identities i ON an.OwnerIdentityID = i.IdentityID
                WHERE i.IdentityType = ? COLLATE UTF8_NOCASE
                ORDER BY an.SortName
            """, (type_lower,))
            return [
                Contributor(
                    contributor_id=row[0],
                    name=row[1],
                    sort_name=row[2],
                    type=row[3] or 'person',
                    matched_alias=row[1] if row[4] == 0 else None  # Mark as alias if not primary
                ) for row in cursor.fetchall()
            ]

    def search(self, query: str) -> List[Contributor]:
        """
        Search for contributors by name or alias, resolving their identity type.
        Uses Unicode-aware case-insensitivity (py_lower).
        """
        with self._credit_repo.get_connection() as conn:
            cursor = conn.cursor()
            # T-Fix: Use py_lower for Unicode-aware case-insensitive search (Ć vs ć)
            q = f"%{query}%"
            cursor.execute("""
                SELECT an.NameID, an.DisplayName, an.SortName, i.IdentityType, an.IsPrimaryName
                FROM ArtistNames an
                LEFT JOIN Identities i ON an.OwnerIdentityID = i.IdentityID
                WHERE py_lower(an.DisplayName) LIKE py_lower(?)
                ORDER BY 
                   CASE WHEN py_lower(an.DisplayName) = py_lower(?) THEN 0 ELSE 1 END,
                   an.SortName
            """, (q, query))
            
            return [
                Contributor(
                    contributor_id=row[0],
                    name=row[1],
                    sort_name=row[2],
                    type=row[3] or 'person',
                    matched_alias=row[1] if row[4] == 0 else None
                ) for row in cursor.fetchall()
            ]

    def get_groups(self, member_id: int) -> List[Contributor]:
        """Get groups this person belongs to."""
        member_identity_id = self._get_identity_id(member_id)
        if not member_identity_id: return []

        with self._credit_repo.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT an.NameID, an.DisplayName, an.SortName, i.IdentityType
                FROM GroupMemberships gm
                JOIN Identities i ON gm.GroupIdentityID = i.IdentityID
                JOIN ArtistNames an ON i.IdentityID = an.OwnerIdentityID
                WHERE gm.MemberIdentityID = ? AND an.IsPrimaryName = 1
                ORDER BY an.SortName
            """
            cursor.execute(query, (member_identity_id,))
            return [
                 Contributor(
                    contributor_id=row[0],
                    name=row[1],
                    sort_name=row[2],
                    type=row[3] or 'group'
                ) for row in cursor.fetchall()
            ]

    def add_member(self, group_id: int, member_id: int, member_alias_id: Optional[int] = None, batch_id: Optional[str] = None) -> bool:
        """Add a member to a group."""
        group_ident = self._get_identity_id(group_id)
        member_ident = self._get_identity_id(member_id)
        
        if not group_ident or not member_ident: return False
        
        # Check if already exists (via SQL or try/except)
        try:
            with self._credit_repo.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO GroupMemberships (GroupIdentityID, MemberIdentityID, CreditedAsNameID, JoinDate)
                    VALUES (?, ?, ?, CURRENT_DATE)
                    ON CONFLICT(GroupIdentityID, MemberIdentityID) DO UPDATE SET
                    CreditedAsNameID = excluded.CreditedAsNameID
                """, (group_ident, member_ident, member_alias_id))
                # Audit Logging
                from src.core.audit_logger import AuditLogger
                if cursor.rowcount > 0:
                    action = "INSERT" # Default to INSERT logic, but could be UPDATE. 
                    # For now we just log the link established.
                    AuditLogger(conn, batch_id=batch_id).log_insert("GroupMemberships", f"{group_ident}-{member_ident}", {
                        "GroupIdentityID": group_ident,
                        "MemberIdentityID": member_ident,
                        "CreditedAsNameID": member_alias_id
                    })
                return cursor.rowcount > 0
        except Exception:
            return False

    def remove_member(self, group_id: int, member_id: int, batch_id: Optional[str] = None) -> bool:
        """Remove a member from a group."""
        group_ident = self._get_identity_id(group_id)
        member_ident = self._get_identity_id(member_id)
        
        if not group_ident or not member_ident: return False
        
        with self._credit_repo.get_connection() as conn:
            cursor = conn.cursor()
            
            # Snapshot for Audit
            from src.core.audit_logger import AuditLogger
            cursor.execute("SELECT GroupIdentityID, MemberIdentityID, CreditedAsNameID FROM GroupMemberships WHERE GroupIdentityID = ? AND MemberIdentityID = ?", (group_ident, member_ident))
            row = cursor.fetchone()
            if not row: return False
            snapshot = {"GroupIdentityID": row[0], "MemberIdentityID": row[1], "CreditedAsNameID": row[2]}

            cursor.execute("""
                DELETE FROM GroupMemberships 
                WHERE GroupIdentityID = ? AND MemberIdentityID = ?
            """, (group_ident, member_ident))
            
            if cursor.rowcount > 0:
                AuditLogger(conn, batch_id=batch_id).log_delete("GroupMemberships", f"{group_ident}-{member_ident}", snapshot)
            return cursor.rowcount > 0

    def get_member_count(self, contributor_id: int) -> int:
        """Count how many group memberships this entity is involved in (as group or member)."""
        identity_id = self._get_identity_id(contributor_id)
        if not identity_id: return 0
        
        with self._credit_repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM GroupMemberships 
                WHERE GroupIdentityID = ? OR MemberIdentityID = ?
            """, (identity_id, identity_id))
            return cursor.fetchone()[0]

    def get_aliases(self, contributor_id: int) -> List[Any]:
        """Get all aliases (non-primary names) for this contributor."""
        identity_id = self._get_identity_id(contributor_id)
        if not identity_id: return []
        
        names = self._name_service.get_by_owner(identity_id)
        # Filter for non-primary
        aliases = []
        for n in names:
            if not n.is_primary_name:
                # Return object structure expected by ArtistAliasAdapter
                # It expects .alias_id and .alias_name
                from types import SimpleNamespace
                aliases.append(SimpleNamespace(alias_id=n.name_id, alias_name=n.display_name))
        return aliases

    def add_alias(self, contributor_id: int, alias_name: str) -> bool:
        """Create a new alias for this contributor."""
        identity_id = self._get_identity_id(contributor_id)
        if not identity_id: return False
        
        try:
            self._name_service.create_name(alias_name, owner_identity_id=identity_id, is_primary=False)
            return True
        except Exception:
            return False

    def delete_alias(self, alias_id: int, batch_id: Optional[str] = None) -> bool:
        """Delete an alias."""
        return self._name_service.delete_name(alias_id, batch_id=batch_id)

    def update_alias(self, alias_id: int, new_name: str, batch_id: Optional[str] = None) -> bool:
        """Rename an alias."""
        name = self._name_service.get_name(alias_id)
        if not name: return False
        name.display_name = new_name
        return self._name_service.update_name(name, batch_id=batch_id)

    def move_alias(self, alias_name: str, old_owner_id: int, new_owner_id: int, batch_id: Optional[str] = None) -> bool:
        """
        Move an alias from one identity to another.
        
        Args:
            alias_name: The display name of the alias to move
            old_owner_id: NameID of the current owner (we resolve to IdentityID)
            new_owner_id: NameID of the new owner (we resolve to IdentityID)
            batch_id: Optional transaction ID
        """
        old_ident = self._get_identity_id(old_owner_id)
        new_ident = self._get_identity_id(new_owner_id)
        if not old_ident or not new_ident:
            return False
        return self._identity_service.move_alias(alias_name, old_ident, new_ident, batch_id=batch_id)

    def abdicate_identity(self, old_id: int, heir_id: int, adopter_id: int, batch_id: Optional[str] = None) -> bool:
        """
        Abdicate an identity: move the primary name to another identity,
        and promote an heir to become the new primary.
        
        Args:
            old_id: NameID of the identity being abdicated from (resolved to IdentityID)
            heir_id: NameID that will become the new primary
            adopter_id: NameID of the identity receiving the old primary (resolved to IdentityID)
        """
        old_ident = self._get_identity_id(old_id)
        adopter_ident = self._get_identity_id(adopter_id)
        
        if not old_ident or not adopter_ident:
            return False
        
        # heir_id is already a NameID, not a ContributorID that needs resolution
        return self._identity_service.abdicate(old_ident, heir_id, adopter_ident, batch_id=batch_id)

