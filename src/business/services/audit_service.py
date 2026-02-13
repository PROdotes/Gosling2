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

    def get_unified_history(self, limit: int = 500) -> List[dict]:
        """Fetch merged view of all data changes and systemic actions."""
        return self.audit_repo.get_unified_log(limit)
