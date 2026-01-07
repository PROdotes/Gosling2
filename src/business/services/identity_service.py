"""
Identity Service
Handles complex identity management logic (Merge, Abdicate, Promote).
Moved from ContributorRepository to improve maintainability and follow SOA.
"""
from typing import Optional, List, Any, Tuple
import sqlite3
from src.core import logger
from src.core.audit_logger import AuditLogger

class IdentityService:
    """Service for managing complex contributor identity transformations."""

    def __init__(self, contributor_repository=None):
        from src.data.repositories.contributor_repository import ContributorRepository
        self._repo = contributor_repository or ContributorRepository()

    def merge(self, source_id: int, target_id: int, create_alias: bool = True, batch_id: Optional[str] = None) -> bool:
        """
        Consolidate source identity into target.
        Transfers all songs, aliases, and relationships.
        """
        try:
            with self._repo.get_connection() as conn:
                cursor = conn.cursor()
                auditor = AuditLogger(conn, batch_id=batch_id)
                
                # Snapshot for Audit (Deleted Source)
                old_c = self._repo.get_by_id(source_id)
                old_snapshot = old_c.to_dict() if old_c else {}

                # 1. Get Source Primary Name
                cursor.execute("SELECT ContributorName FROM Contributors WHERE ContributorID = ?", (source_id,))
                res = cursor.fetchone()
                if not res: return False
                s_name = res[0]
                
                # 2. Source Name becomes an alias for target (Optional)
                source_name_alias_id = None
                if create_alias:
                    cursor.execute("INSERT OR IGNORE INTO ContributorAliases (ContributorID, AliasName) VALUES (?, ?)", (target_id, s_name))
                    new_alias_id = cursor.lastrowid
                    if new_alias_id:
                        auditor.log_insert("ContributorAliases", new_alias_id, {"ContributorID": target_id, "AliasName": s_name})
                    
                    cursor.execute("SELECT AliasID FROM ContributorAliases WHERE ContributorID = ? AND AliasName = ?", (target_id, s_name))
                    row = cursor.fetchone()
                    source_name_alias_id = row[0] if row else None
                
                # 3. Transfer existing Aliases
                cursor.execute("SELECT AliasID, AliasName FROM ContributorAliases WHERE ContributorID = ?", (source_id,))
                moving_aliases = cursor.fetchall()
                for a_id, a_name in moving_aliases:
                    auditor.log_update("ContributorAliases", a_id, 
                        {"ContributorID": source_id, "AliasName": a_name},
                        {"ContributorID": target_id, "AliasName": a_name}
                    )
                cursor.execute("UPDATE OR IGNORE ContributorAliases SET ContributorID = ? WHERE ContributorID = ?", (target_id, source_id))
                
                # 4. Transfer Song Roles
                cursor.execute("""
                    SELECT SourceID, RoleID FROM MediaSourceContributorRoles 
                    WHERE ContributorID = ? AND (SourceID, RoleID) IN (
                        SELECT SourceID, RoleID FROM MediaSourceContributorRoles WHERE ContributorID = ?
                    )
                """, (source_id, target_id))
                duplicates = cursor.fetchall()
                for s_id, r_id in duplicates:
                     auditor.log_delete("MediaSourceContributorRoles", f"{s_id}-{source_id}-{r_id}", 
                         {"SourceID": s_id, "ContributorID": source_id, "RoleID": r_id})

                cursor.execute("""
                    DELETE FROM MediaSourceContributorRoles 
                    WHERE ContributorID = ? AND (SourceID, RoleID) IN (
                        SELECT SourceID, RoleID FROM MediaSourceContributorRoles WHERE ContributorID = ?
                    )
                """, (source_id, target_id))
                
                cursor.execute("SELECT SourceID, RoleID FROM MediaSourceContributorRoles WHERE ContributorID = ?", (source_id,))
                moving_roles = cursor.fetchall()
                for s_id, r_id in moving_roles:
                     auditor.log_update("MediaSourceContributorRoles", f"{s_id}-{source_id}-{r_id}", 
                         {"ContributorID": source_id}, {"ContributorID": target_id})

                if source_name_alias_id:
                     cursor.execute("""
                        UPDATE MediaSourceContributorRoles 
                        SET ContributorID = ?, 
                            CreditedAliasID = COALESCE(CreditedAliasID, ?)
                        WHERE ContributorID = ?
                     """, (target_id, source_name_alias_id, source_id))
                else:
                     cursor.execute("""
                        UPDATE MediaSourceContributorRoles 
                        SET ContributorID = ?,
                            CreditedAliasID = NULL
                        WHERE ContributorID = ?
                     """, (target_id, source_id))
                
                # 5. Transfer Group Memberships
                # Cleanup duplicates
                cursor.execute("""
                    DELETE FROM GroupMembers 
                    WHERE MemberID = ? AND GroupID IN (
                        SELECT GroupID FROM GroupMembers WHERE MemberID = ?
                    )
                """, (source_id, target_id))
                
                cursor.execute("SELECT GroupID, MemberAliasID FROM GroupMembers WHERE MemberID = ?", (source_id,))
                moving_memberships = cursor.fetchall()
                for gid, old_alias_id in moving_memberships:
                     auditor.log_update("GroupMembers", f"{gid}-{source_id}", 
                         {"MemberID": source_id}, {"MemberID": target_id})

                # If we created a new alias for the source name, use it for memberships too
                if source_name_alias_id:
                     cursor.execute("""
                        UPDATE GroupMembers 
                        SET MemberID = ?, 
                            MemberAliasID = COALESCE(MemberAliasID, ?)
                        WHERE MemberID = ?
                     """, (target_id, source_name_alias_id, source_id))
                else:
                     cursor.execute("UPDATE GroupMembers SET MemberID = ? WHERE MemberID = ?", (target_id, source_id))

                # 6. Delete Source Contributor
                cursor.execute("DELETE FROM Contributors WHERE ContributorID = ?", (source_id,))
                auditor.log_delete("Contributors", source_id, old_snapshot)
                
                return True
        except Exception as e:
            logger.error(f"Error merging contributor {source_id} into {target_id}: {e}")
            return False

    def abdicate_identity(self, current_id: int, heir_alias_id: int, target_parent_id: int, batch_id: Optional[str] = None) -> bool:
        """
        'Peel & Move':
        1. Promotes 'heir_alias_id' to be the Primary Name of 'current_id'.
        2. Creates a NEW alias for the OLD Primary Name attached to 'target_parent_id'.
        3. 'current_id' survives (with songs/other aliases) but has a new name.
        """
        try:
            with self._repo.get_connection() as conn:
                cursor = conn.cursor()
                auditor = AuditLogger(conn, batch_id=batch_id)
                
                # 1. Get info
                cursor.execute("SELECT ContributorName FROM Contributors WHERE ContributorID = ?", (current_id,))
                res = cursor.fetchone()
                if not res: return False
                old_primary_name = res[0]
                
                cursor.execute("SELECT AliasName FROM ContributorAliases WHERE AliasID = ?", (heir_alias_id,))
                res = cursor.fetchone()
                if not res: return False
                heir_name = res[0]
                
                # 2. Promote Heir (Rename ID)
                cursor.execute("UPDATE Contributors SET ContributorName = ? WHERE ContributorID = ?", (heir_name, current_id))
                
                # 3. Delete Heir Alias Record (It is now primary)
                cursor.execute("DELETE FROM ContributorAliases WHERE AliasID = ?", (heir_alias_id,))
                
                # 4. Create Old Name as Alias on TARGET
                cursor.execute("INSERT INTO ContributorAliases (ContributorID, AliasName) VALUES (?, ?)", (target_parent_id, old_primary_name))
                new_alias_id = cursor.lastrowid
                if new_alias_id:
                    auditor.log_insert("ContributorAliases", new_alias_id, {"ContributorID": target_parent_id, "AliasName": old_primary_name})

                # 5. MOVE OTHER ALIASES
                cursor.execute("""
                    SELECT AliasID, AliasName FROM ContributorAliases 
                    WHERE ContributorID = ? AND AliasID != ?
                """, (current_id, heir_alias_id))
                moving_aliases = cursor.fetchall()
                for a_id, a_name in moving_aliases:
                    auditor.log_update("ContributorAliases", a_id, 
                        {"ContributorID": current_id}, {"ContributorID": target_parent_id})
                
                cursor.execute("""
                    UPDATE ContributorAliases 
                    SET ContributorID = ? 
                    WHERE ContributorID = ? AND AliasID != ?
                """, (target_parent_id, current_id, heir_alias_id))

                # 6. MOVE CREDITS
                # A. Move Primary Credits (Freddie) -> Target + New Alias
                cursor.execute("""
                    UPDATE MediaSourceContributorRoles 
                    SET ContributorID = ?, CreditedAliasID = ?
                    WHERE ContributorID = ? AND CreditedAliasID IS NULL
                """, (target_parent_id, new_alias_id, current_id))
                
                # B. Move Credits for Other Aliases -> Target (Keep Alias ID)
                cursor.execute("""
                    UPDATE MediaSourceContributorRoles 
                    SET ContributorID = ?
                    WHERE ContributorID = ? AND CreditedAliasID IS NOT NULL AND CreditedAliasID != ?
                """, (target_parent_id, current_id, heir_alias_id))
                
                # 7. MOVE GROUP MEMBERSHIPS
                # a. Delete duplicates
                cursor.execute("""
                    DELETE FROM GroupMembers 
                    WHERE MemberID = ? AND GroupID IN (
                        SELECT GroupID FROM GroupMembers WHERE MemberID = ?
                    )
                """, (current_id, target_parent_id))
                
                # b. Move remaining memberships
                cursor.execute("SELECT GroupID, MemberAliasID FROM GroupMembers WHERE MemberID = ?", (current_id,))
                memberships = cursor.fetchall()
                for gid, old_alias_id in memberships:
                    auditor.log_update("GroupMembers", f"{gid}-{current_id}", 
                        {"MemberID": current_id}, {"MemberID": target_parent_id, "MemberAliasID": new_alias_id})

                cursor.execute("""
                    UPDATE GroupMembers 
                    SET MemberID = ?, MemberAliasID = ?
                    WHERE MemberID = ?
                """, (target_parent_id, new_alias_id, current_id))

                auditor.log_action("IDENTITY_ABDICATION", "Contributors", current_id, 
                    f"Renamed to {heir_name}; '{old_primary_name}' credits moved to {target_parent_id}")
                
                return True
        except Exception as e:
            logger.error(f"Error abdicating identity {current_id}: {e}")
            return False

    def promote_alias(self, contributor_id: int, alias_id: int, batch_id: Optional[str] = None) -> bool:
        """Swap an alias to becomes the primary name of an identity."""
        try:
            with self._repo.get_connection() as conn:
                cursor = conn.cursor()
                auditor = AuditLogger(conn, batch_id=batch_id)
                
                # 1. Get current names
                cursor.execute("SELECT ContributorName FROM Contributors WHERE ContributorID = ?", (contributor_id,))
                old_primary = cursor.fetchone()[0]
                
                cursor.execute("SELECT AliasName FROM ContributorAliases WHERE AliasID = ?", (alias_id,))
                new_primary = cursor.fetchone()[0]
                
                # 2. Update Contributor Record
                cursor.execute("UPDATE Contributors SET ContributorName = ? WHERE ContributorID = ?", (new_primary, contributor_id))
                auditor.log_update("Contributors", contributor_id, {"ContributorName": old_primary}, {"ContributorName": new_primary})
                
                # 3. Swap Alias Record (Old primary becomes a new alias)
                cursor.execute("UPDATE ContributorAliases SET AliasName = ? WHERE AliasID = ?", (old_primary, alias_id))
                auditor.log_update("ContributorAliases", alias_id, {"AliasName": new_primary}, {"AliasName": old_primary})
                
                # 4. SWAP CREDITS (Identity Logic)
                # Primary credits (NULL alias) now point to the NEW alias.
                # Credits specifically to the alias (which is now primary) become NULL.
                cursor.execute("""
                    UPDATE MediaSourceContributorRoles
                    SET CreditedAliasID = CASE
                        WHEN CreditedAliasID IS NULL THEN ?
                        WHEN CreditedAliasID = ? THEN NULL
                        ELSE CreditedAliasID
                    END
                    WHERE ContributorID = ? 
                      AND (CreditedAliasID IS NULL OR CreditedAliasID = ?)
                """, (alias_id, alias_id, contributor_id, alias_id))
                
                return True
        except Exception as e:
            logger.error(f"Error promoting alias {alias_id}: {e}")
            return False

    def move_alias(self, alias_name: str, old_owner_id: int, new_owner_id: int, batch_id: Optional[str] = None) -> bool:
        """Transfer Alias ownership from one identity to another."""
        try:
            with self._repo.get_connection() as conn:
                cursor = conn.cursor()
                auditor = AuditLogger(conn, batch_id=batch_id)
                
                # 1. Transfer Alias Record
                cursor.execute("SELECT AliasID FROM ContributorAliases WHERE ContributorID = ? AND AliasName = ?", (old_owner_id, alias_name))
                row = cursor.fetchone()
                if not row: return False
                alias_id = row[0]
                
                cursor.execute("UPDATE ContributorAliases SET ContributorID = ? WHERE AliasID = ?", (new_owner_id, alias_id))
                auditor.log_update("ContributorAliases", alias_id, {"ContributorID": old_owner_id}, {"ContributorID": new_owner_id})
                
                # 2. Transfer associated credits
                cursor.execute("SELECT SourceID, RoleID FROM MediaSourceContributorRoles WHERE ContributorID = ? AND CreditedAliasID = ?", (old_owner_id, alias_id))
                for s_id, r_id in cursor.fetchall():
                     auditor.log_update("MediaSourceContributorRoles", f"{s_id}-{old_owner_id}-{r_id}", 
                         {"ContributorID": old_owner_id}, {"ContributorID": new_owner_id})
                         
                cursor.execute("""
                    UPDATE MediaSourceContributorRoles 
                    SET ContributorID = ? 
                    WHERE ContributorID = ? AND CreditedAliasID = ?
                """, (new_owner_id, old_owner_id, alias_id))
                
                return True
        except Exception as e:
            logger.error(f"Error moving alias {alias_name}: {e}")
            return False
