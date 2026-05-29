from fastapi import APIRouter

from src.data.audit_repository import AuditRepository
from src.engine.config import get_db_path

router = APIRouter()


@router.get("/api/v1/audit/changelog")
def get_changelog(limit: int = 500):
    db_path = str(get_db_path())
    repo = AuditRepository(db_path)
    with repo._get_connection() as conn:
        return {"batches": repo.get_changelog(conn, limit)}
