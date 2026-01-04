"""
Audit Logging Service

Centralized logging of all data changes and user actions.
Follows the 'Smart Logger, Dumb Repository' pattern.
"""
from typing import Optional, Dict, Any, List
import json
import uuid
import datetime
from src.core import logger

class AuditLogger:
    """
    Handles calculating diffs and dispatching to AuditRepository.
    Requires an active database connection.
    """

    def __init__(self, connection):
        # Local import to avoid circular dependency if repositories import core
        from src.data.repositories.audit_repository import AuditRepository
        self.audit_repo = AuditRepository(connection=connection)
        self.batch_id = str(uuid.uuid4())

    def log_insert(self, table_name: str, record_id: int, new_data: Dict[str, Any]) -> None:
        """Log a newly inserted record."""
        if not new_data:
            return

        # Flatten/normalize data before logging
        normalized = self._normalize_dict(new_data)
        
        rows = []
        for field, value in normalized.items():
            if value is not None:
                rows.append((table_name, record_id, field, None, value, self.batch_id))
        
        self.audit_repo.insert_change_logs(rows)

    def log_update(self, table_name: str, record_id: int, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> None:
        """
        Log update to an existing record.
        Calculates diff between old_data and new_data. Logs one row per changed field.
        """
        if not old_data or not new_data:
            return

        diffs = self._compute_diff(old_data, new_data)
        if not diffs:
            return # No actual changes

        rows = []
        for field, change in diffs.items():
            rows.append((
                table_name, 
                record_id, 
                field, 
                change['old'], 
                change['new'], 
                self.batch_id
            ))
        
        self.audit_repo.insert_change_logs(rows)

    def log_delete(self, table_name: str, record_id: int, old_data: Dict[str, Any]) -> None:
        """
        Log deletion of a record.
        1. Writes full snapshot to DeletedRecords (Recycle Bin).
        2. Writes field-level markers to ChangeLog for visibility.
        """
        if not old_data:
            return

        # 1. Archive to DeletedRecords
        serialized_snapshot = json.dumps(old_data, default=str)
        self.audit_repo.insert_deleted_record(table_name, record_id, serialized_snapshot, self.batch_id)

        # 2. Add to ChangeLog so it shows up in "Data History"
        normalized = self._normalize_dict(old_data)
        rows = []
        for field, value in normalized.items():
            if value is not None:
                rows.append((table_name, record_id, field, value, None, self.batch_id))
        
        if rows:
            self.audit_repo.insert_change_logs(rows)

    def log_action(self, action_type: str, target_table: str = None, target_id: int = None, details: Any = None, user_id: str = None) -> None:
        """
        Log a high-level user action (e.g. "Imported File", "Added to Playlist").
        """
        details_json = json.dumps(details, default=str) if details else None
        self.audit_repo.insert_action_log(action_type, target_table, target_id, details_json, user_id, self.batch_id)


    # --- INTERNAL HELPERS ---

    def _normalize_dict(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Convert all nested types (lists, objects) to consistent strings for storage."""
        normalized = {}
        for k, v in data.items():
            if v is None:
                normalized[k] = None
                continue
            
            # List Handling: Sort and Join
            if isinstance(v, list):
                # Filter None/Empty, convert to string, sort
                items = sorted([str(x).strip() for x in v if x])
                val = ", ".join(items)
                normalized[k] = val if val else None # Normalize empty list to None
                
            # Bool Handling: explicit 0/1 
            elif isinstance(v, bool):
                normalized[k] = "1" if v else "0"
                
            # Primitives: Convert to string, normalize empty to None
            else:
                s_val = str(v).strip()
                normalized[k] = s_val if s_val else None
                
        return normalized

    def _compute_diff(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """
        Compare old vs new. Returns { field: {'old': str, 'new': str} }
        """
        diffs = {}
        
        # Normalize both sides to predictable strings
        norm_old = self._normalize_dict(old)
        norm_new = self._normalize_dict(new)
        
        # Get all keys
        all_keys = set(norm_old.keys()) | set(norm_new.keys())
        
        # Filter hidden/internal keys
        # TODO: Define list of ignored keys if any (e.g. internal _is_dirty flags)
        
        for k in all_keys:
            val_old = norm_old.get(k)
            val_new = norm_new.get(k)
            
            # Strict string equality check
            if val_old != val_new:
                # If both are effectively empty (None vs "")?
                # _normalize_dict leaves None as None, Strings as Strings.
                # If we want to treat None and "" as same, do it there.
                # For now, explicit change None -> "" is a change.
                diffs[k] = {'old': val_old, 'new': val_new}
                
        return diffs
