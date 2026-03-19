from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from src.services.audit_service import AuditService
from src.services.logger import logger
import os

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


def _get_service() -> AuditService:
    """Centralized service factory for the router."""
    db_path = os.getenv("GOSLING_DB_PATH", "sqldb/gosling2.db")
    return AuditService(db_path)


@router.get("/history/{table}/{record_id:int}")
async def get_history(table: str, record_id: int) -> List[Dict[str, Any]]:
    """
    Fetch the complete unified audit timeline for a record.
    Matches ActionLog, ChangeLog, and DeletedRecords snapshots.
    """
    logger.info(f"[AuditRouter] GET /history/{table}/{record_id}")

    # We should probably validate the table name against a whitelist in the future
    try:
        history = _get_service().get_history(record_id, table)
        if not history:
            logger.debug(f"[AuditRouter] No history found for {table}:{record_id}")
            # Returning empty list is fine for history
            return []
        return history
    except Exception as e:
        logger.error(
            f"[AuditRouter] ERROR: Failed to fetch history for {table}:{record_id} - {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Internal audit processing failure")
