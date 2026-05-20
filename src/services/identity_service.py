from typing import List, Optional
from src.data.identity_repository import IdentityRepository
from src.models.domain import Identity
from src.models.view_models import ArtistChipView
from src.services.logger import logger
from src.utils.text import normalize_for_search


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

    def get_all_slim(self) -> List[dict]:
        """Fetch slim list-view rows for all active identities (no hydration)."""
        logger.debug("[IdentityService] -> get_all_slim()")
        result = self._identity_repo.get_all_slim()
        logger.debug(f"[IdentityService] <- get_all_slim() count={len(result)}")
        return result

    def search_slim(self, query: str, exclude_groups: bool = False) -> List[dict]:
        """Slim list-view search (no hydration). Matches DisplayName, LegalName, or Alias."""
        logger.debug(f"[IdentityService] -> search_slim(q='{query}')")
        result = self._identity_repo.search_slim(
            normalize_for_search(query), exclude_groups=exclude_groups
        )
        logger.debug(
            f"[IdentityService] <- search_slim(q='{query}') count={len(result)}"
        )
        return result

    def resolve_identity_by_name(self, display_name: str) -> Optional[int]:
        """Return the IdentityID for an ArtistName (Truth-First resolution)."""
        return self._identity_repo.find_identity_by_name(display_name)

    def search_artist_names(
        self, query: str, exclude_groups: bool = False
    ) -> List[ArtistChipView]:
        """Search ArtistNames (one row per name) for picker results."""
        logger.debug(
            f"[IdentityService] -> search_artist_names(q='{query}', exclude_groups={exclude_groups})"
        )
        rows = self._identity_repo.search_artist_names(
            normalize_for_search(query), exclude_groups=exclude_groups
        )
        result = [
            ArtistChipView(
                name_id=r["NameID"],
                display_name=r["DisplayName"],
                owner_identity_id=r["OwnerIdentityID"],
            )
            for r in rows
        ]
        logger.debug(
            f"[IdentityService] <- search_artist_names(q='{query}') count={len(result)}"
        )
        return result


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
