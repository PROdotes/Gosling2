"""
Audit Service

Provides business logic for retrieving and managing Audit Logs.
"""
from typing import List, Optional
from ...data.repositories.audit_repository import AuditRepository

class AuditService:
    """Service for accessing system audit history."""
    
    def __init__(self, audit_repository: Optional[AuditRepository] = None):
        # Allow passing an existing repository or create a new one (BaseRepository will find path)
        self.audit_repo = audit_repository or AuditRepository()

    def get_recent_changes(self, limit: int = 1000) -> List[dict]:
        """Fetch recent field-level changes."""
        return self.audit_repo.get_change_log(limit)

    def get_recent_actions(self, limit: int = 1000) -> List[dict]:
        """Fetch high-level system actions."""
        return self.audit_repo.get_action_log(limit)

    def get_unified_history(self, limit: int = 500) -> List[dict]:
        """Fetch merged view of all data changes and systemic actions."""
        return self.audit_repo.get_unified_log(limit)

    def log_custom_action(self, action_type: str, details: dict, target_table: str = None, target_id: int = None):
        """Allows services to log custom high-level actions."""
        import json
        details_json = json.dumps(details)
        self.audit_repo.insert_action_log(action_type, target_table, target_id, details_json, user_id="SYSTEM")
