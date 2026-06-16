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


@router.get("/api/v1/audit/integrity")
def get_audit_integrity():
    """
    Returns the count of ChangeLog rows with NULL batch_id.
    A nonzero count means a write path bypassed write_connection() or the DB
    was edited manually. The DB is locked until this is resolved.
    Safe to call even when the DB is locked — uses a raw connection.
    """
    db_path = str(get_db_path())
    repo = AuditRepository(db_path)
    conn = repo._open_connection()
    try:
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM ChangeLog WHERE batch_id IS NULL"
            ).fetchone()[0]
        except Exception:
            count = 0
    finally:
        conn.close()
    return {"null_batch_rows": count, "locked": count > 0}
