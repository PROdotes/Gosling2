from typing import List, Optional
from src.data.identity_repository import IdentityRepository
from src.models.domain import Identity
from src.services.logger import logger


class IdentityService:
    """Specialized orchestrator for Identity-domain logic (Persons, Groups, Aliases)."""

    def __init__(
        self, db_path: str, identity_repo: Optional[IdentityRepository] = None
    ):
        self._db_path = db_path
        self._identity_repo = identity_repo or IdentityRepository(db_path)

    def get_identity(self, identity_id: int) -> Optional[Identity]:
        """Fetch a full identity tree (Aliases/Members/Groups)."""
        logger.debug(f"[IdentityService] -> get_identity(id={identity_id})")
        identity = self._identity_repo.get_by_id(identity_id)
        if not identity:
            logger.warning(f"[IdentityService] Exit: Identity {identity_id} not found.")
            return None

        hydrated_list = self._hydrate_identities([identity])
        if not hydrated_list:
            return None

        result = hydrated_list[0]
        logger.debug(
            f"[IdentityService] <- get_identity(id={identity_id}) '{result.display_name}'"
        )
        return result

    def get_all_identities(self) -> List[Identity]:
        """Fetch a list of all active identities."""
        logger.debug("[IdentityService] -> get_all_identities()")
        identities = self._identity_repo.get_all_identities()
        result = self._hydrate_identities(identities)
        logger.debug(f"[IdentityService] <- get_all_identities() count={len(result)}")
        return result

    def resolve_identity_by_name(self, display_name: str) -> Optional[int]:
        """Return the IdentityID for an ArtistName (Truth-First resolution)."""
        return self._identity_repo.find_identity_by_name(display_name)

    def add_identity_alias(
        self, identity_id: int, display_name: str, name_id: Optional[int] = None
    ) -> int:
        """Link a new or existing alias name to an identity (Truth-First mapping)."""
        logger.debug(
            f"[IdentityService] -> add_identity_alias(id={identity_id}, name='{display_name}', name_id={name_id})"
        )
        # 1. Existence check (Banker Mode)
        identity = self._identity_repo.get_by_id(identity_id)
        if not identity:
            raise LookupError(f"Identity {identity_id} not found")

        # 2. Add via repo (Transactional)
        with self._identity_repo.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Prioritize explicit ID link over string search
                result_name_id = self._identity_repo.add_alias(
                    identity_id, display_name, cursor, name_id=name_id
                )
                conn.commit()
                logger.debug(
                    f"[IdentityService] <- add_identity_alias() OK, result_name_id={result_name_id}"
                )
                return result_name_id
            except Exception as e:
                conn.rollback()
                logger.error(f"[IdentityService] add_identity_alias failed: {e}")
                raise e

    def remove_identity_alias(self, name_id: int) -> None:
        """Remove an alias from an identity. Raises ValueError if it is the primary name."""
        logger.debug(f"[IdentityService] -> remove_identity_alias(name_id={name_id})")
        with self._identity_repo.get_connection() as conn:
            cursor = conn.cursor()
            try:
                self._identity_repo.delete_alias(name_id, cursor)
                conn.commit()
                logger.debug(
                    f"[IdentityService] <- remove_identity_alias(name_id={name_id}) OK"
                )
            except ValueError:
                conn.rollback()
                raise
            except Exception as e:
                conn.rollback()
                logger.error(f"[IdentityService] remove_identity_alias failed: {e}")
                raise

    def update_identity_legal_name(
        self, identity_id: int, legal_name: Optional[str]
    ) -> None:
        """Update the LegalName on an Identity. Raises LookupError if not found."""
        logger.debug(
            f"[IdentityService] -> update_identity_legal_name(id={identity_id}, name={legal_name!r})"
        )
        with self._identity_repo.get_connection() as conn:
            try:
                self._identity_repo.update_legal_name(identity_id, legal_name, conn)
                conn.commit()
            except LookupError:
                conn.rollback()
                raise
            except Exception as e:
                conn.rollback()
                logger.error(
                    f"[IdentityService] update_identity_legal_name failed: {e}"
                )
                raise

    def search_identities(self, query: str, exclude_groups: bool = False) -> List[Identity]:
        """Search for identities by name or alias."""
        logger.debug(f"[IdentityService] -> search_identities(q='{query}')")
        identities = self._identity_repo.search_identities(query, exclude_groups=exclude_groups)
        result = self._hydrate_identities(identities)
        logger.debug(
            f"[IdentityService] <- search_identities(q='{query}') count={len(result)}"
        )
        return result

    def get_identity_song_counts(self, identity_ids: List[int]) -> dict:
        """Batch active song counts for identities (across all aliases). Returns {id: N}."""
        return self._identity_repo.get_song_counts_batch(identity_ids)

    def merge_identity_into(self, source_name_id: int, target_name_id: int) -> None:
        """Merges a solo identity into an existing one. Delegates to IdentityRepository."""
        logger.info(
            f"[IdentityService] -> merge_identity_into(source={source_name_id}, target={target_name_id})"
        )
        conn = self._identity_repo.get_connection()
        try:
            cursor = conn.cursor()
            self._identity_repo.merge_orphan_into(
                source_name_id, target_name_id, cursor
            )
            conn.commit()
            logger.info("[IdentityService] <- merge_identity_into OK")
        except Exception as e:
            conn.rollback()
            logger.error(f"[IdentityService] <- merge_identity_into FAILED: {e}")
            raise
        finally:
            conn.close()

    def set_identity_type(self, identity_id: int, type_: str) -> None:
        """Convert an identity between person and group."""
        logger.debug(
            f"[IdentityService] -> set_identity_type(id={identity_id}, type={type_!r})"
        )
        with self._identity_repo.get_connection() as conn:
            try:
                self._identity_repo.set_type(identity_id, type_, conn)
                conn.commit()
            except (LookupError, ValueError):
                conn.rollback()
                raise
            except Exception as e:
                conn.rollback()
                logger.error(f"[IdentityService] set_identity_type failed: {e}")
                raise

    def add_identity_member(self, group_id: int, member_id: int) -> None:
        """Add a person identity as a member of a group."""
        logger.debug(
            f"[IdentityService] -> add_identity_member(group={group_id}, member={member_id})"
        )
        with self._identity_repo.get_connection() as conn:
            cursor = conn.cursor()
            try:
                self._identity_repo.add_member(group_id, member_id, cursor)
                conn.commit()
            except (LookupError, ValueError):
                conn.rollback()
                raise
            except Exception as e:
                conn.rollback()
                logger.error(f"[IdentityService] add_identity_member failed: {e}")
                raise

    def remove_identity_member(self, group_id: int, member_id: int) -> None:
        """Remove a member from a group. Noop if not linked."""
        logger.debug(
            f"[IdentityService] -> remove_identity_member(group={group_id}, member={member_id})"
        )
        with self._identity_repo.get_connection() as conn:
            cursor = conn.cursor()
            try:
                self._identity_repo.remove_member(group_id, member_id, cursor)
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"[IdentityService] remove_identity_member failed: {e}")
                raise

    def delete_unlinked_identities(self, identity_ids: List[int]) -> int:
        """
        Soft-delete identities from the given list that have zero active songs/albums across ALL aliases.
        """
        logger.debug(
            f"[IdentityService] -> delete_unlinked_identities(count={len(identity_ids)})"
        )
        if not identity_ids:
            return 0

        conn = self._identity_repo.get_connection()
        try:
            deleted = 0
            for identity_id in identity_ids:
                if not self._identity_repo.get_song_ids_by_identity(
                    identity_id, conn
                ) and not self._identity_repo.get_album_ids_by_identity(
                    identity_id, conn
                ):
                    if self._identity_repo.soft_delete(identity_id, conn):
                        deleted += 1
            conn.commit()
            logger.info(
                f"[IdentityService] <- delete_unlinked_identities() deleted={deleted}"
            )
            return deleted
        except Exception as e:
            conn.rollback()
            logger.error(f"[IdentityService] <- delete_unlinked_identities FAILED: {e}")
            raise
        finally:
            conn.close()

    def _hydrate_identities(self, identities: List[Identity]) -> List[Identity]:
        """Centralized batch hydration for identities and their relations."""
        identities = [i for i in identities if i is not None]
        if not identities:
            return []

        identity_ids = [i.id for i in identities]
        logger.debug(
            f"[IdentityService] -> _hydrate_identities(count={len(identity_ids)})"
        )

        aliases_by_id = self._identity_repo.get_aliases_batch(identity_ids)
        members_by_id = self._identity_repo.get_members_batch(identity_ids)
        groups_by_id = self._identity_repo.get_groups_batch(identity_ids)

        hydrated = []
        for identity in identities:
            hydrated.append(
                identity.model_copy(
                    update={
                        "aliases": aliases_by_id.get(identity.id, []),
                        "members": members_by_id.get(identity.id, []),
                        "groups": groups_by_id.get(identity.id, []),
                    }
                )
            )
        logger.debug(f"[IdentityService] <- _hydrate_identities(count={len(hydrated)})")
        return hydrated
