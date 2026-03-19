from typing import List, Dict, Any
from src.data.audit_repository import AuditRepository
from src.services.logger import logger


class AuditService:
    """Orchestrates audit history logs and snapshots."""

    def __init__(self, db_path: str):
        self._audit_repo = AuditRepository(db_path)

    def get_history(self, record_id: int, table: str) -> List[Dict[str, Any]]:
        """
        Retrieves a unified timeline of actions and changes for a record.
        Merges ActionLog and ChangeLog entries, sorted by timestamp.
        """
        logger.info(
            f"[AuditService] Entry: get_history(id={record_id}, table='{table}')"
        )

        actions = self._audit_repo.get_actions_for_target(record_id, table)
        changes = self._audit_repo.get_changes_for_record(record_id, table)
        deleted = self._audit_repo.get_deleted_snapshot(record_id, table)

        timeline = []

        # 1. Add Actions to timeline
        for action in actions:
            timeline.append(
                {
                    "timestamp": action.timestamp,
                    "type": "ACTION",
                    "label": action.action_type,
                    "details": action.details,
                    "user": action.user_id,
                    "batch": action.batch_id,
                }
            )

        # 2. Add Changes to timeline
        for change in changes:
            label = f"Updated {change.field_name}"
            # Give clear context for related table modifications (like SongCredits)
            if change.table_name != table:
                label = f"[{change.table_name}] {label}"

            timeline.append(
                {
                    "timestamp": change.timestamp,
                    "type": "CHANGE",
                    "label": label,
                    "old": change.old_value,
                    "new": change.new_value,
                    "batch": change.batch_id,
                }
            )

        # 3. Add Deletion status if exists
        if deleted:
            timeline.append(
                {
                    "timestamp": deleted.deleted_at,
                    "type": "LIFECYCLE",
                    "label": "RECORD DELETED",
                    "snapshot": deleted.snapshot,  # User may want to inspect this
                    "batch": deleted.batch_id,
                }
            )

        # Sort timeline descending (newest first)
        timeline.sort(key=lambda x: x["timestamp"] or "", reverse=True)

        logger.info(f"[AuditService] Exit: Returning {len(timeline)} timeline events.")
        return timeline
