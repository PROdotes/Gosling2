import sqlite3

from src.data.base_repository import BaseRepository


class AuditRepository(BaseRepository):
    def get_changelog(self, conn: sqlite3.Connection, limit: int = 500) -> list:
        cursor = conn.execute(
            "SELECT id, batch_id, batch_label, changed_at, table_name, entity_id, "
            "field_name, old_value, new_value FROM ChangeLog ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        cols = [d[0] for d in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]

        batches: dict = {}
        batch_order: list = []
        for row in rows:
            bid = row["batch_id"] or "(pending)"
            if bid not in batches:
                batch_order.append(bid)
                batches[bid] = {
                    "batch_id": bid,
                    "batch_label": row["batch_label"],
                    "timestamp": row["changed_at"],
                    "rows": [],
                }
            batches[bid]["rows"].append(row)

        result = []
        for bid in batch_order:
            b = batches[bid]
            b["rows"].reverse()
            result.append(b)
        return result
