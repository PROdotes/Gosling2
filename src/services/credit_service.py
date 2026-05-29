from typing import List, Optional
import sqlite3

from src.data.song_credit_repository import SongCreditRepository
from src.models.domain import SongCredit
from src.services.logger import logger
from src.utils.text import normalize_for_search


class CreditService:
    """Specialized orchestrator for credit-domain logic (Artists, Roles, Names)."""

    def __init__(
        self, db_path: str, credit_repo: Optional[SongCreditRepository] = None
    ):
        self._db_path = db_path
        self._credit_repo = credit_repo or SongCreditRepository(db_path)

    def insert_credits(
        self, source_id: int, credits: List[SongCredit], conn: sqlite3.Connection
    ) -> None:
        """Insert credits with normalized display names for search."""
        logger.debug(
            f"[CreditService] -> insert_credits(source_id={source_id}, count={len(credits)})"
        )
        if not credits:
            logger.debug("[CreditService] <- insert_credits() empty list, no-op")
            return

        cursor = conn.cursor()
        values_to_insert = []
        for credit in credits:
            role_id = self._credit_repo.get_or_create_role(credit.role_name, cursor)
            display_name_search = normalize_for_search(credit.display_name)
            name_id = self._credit_repo.get_or_create_credit_name(
                credit.display_name,
                cursor,
                identity_id=credit.identity_id,
                display_name_search=display_name_search,
            )
            values_to_insert.append((source_id, name_id, role_id))

        if values_to_insert:
            cursor.executemany(
                "INSERT OR IGNORE INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
                values_to_insert,
            )

        logger.info(
            f"[CreditService] <- insert_credits(source_id={source_id}) wrote {len(credits)} credits"
        )

    def add_credit(
        self,
        source_id: int,
        display_name: str,
        role_name: str,
        conn: sqlite3.Connection,
        identity_id: Optional[int] = None,
    ) -> SongCredit:
        """Add a single credit with normalized display name."""
        logger.debug(
            f"[CreditService] -> add_credit(source_id={source_id}, name='{display_name}', role='{role_name}')"
        )
        display_name_search = normalize_for_search(display_name)
        result = self._credit_repo.add_credit(
            source_id,
            display_name,
            role_name,
            conn,
            identity_id=identity_id,
            display_name_search=display_name_search,
        )
        logger.info(
            f"[CreditService] <- add_credit(source_id={source_id}) added '{display_name}'"
        )
        return result

    def remove_credit(self, credit_id: int, conn: sqlite3.Connection) -> None:
        """Remove a credit by ID."""
        logger.debug(f"[CreditService] -> remove_credit(credit_id={credit_id})")
        self._credit_repo.remove_credit(credit_id, conn)
        logger.info(f"[CreditService] <- remove_credit(credit_id={credit_id}) removed")

    def update_credit_name(
        self, name_id: int, new_name: str, conn: sqlite3.Connection
    ) -> int:
        """Update a credit name with normalized search shadow."""
        logger.debug(
            f"[CreditService] -> update_credit_name(name_id={name_id}, new_name='{new_name}')"
        )
        new_name_search = normalize_for_search(new_name)
        rowcount = self._credit_repo.update_credit_name(
            name_id, new_name, conn, new_name_search=new_name_search
        )
        logger.info(
            f"[CreditService] <- update_credit_name(name_id={name_id}) updated {rowcount} rows"
        )
        return rowcount

    def get_all_roles(self) -> List[str]:
        """Fetch all available role names."""
        logger.debug("[CreditService] -> get_all_roles()")
        result = self._credit_repo.get_all_roles()
        logger.info(f"[CreditService] <- get_all_roles() count={len(result)}")
        return result
