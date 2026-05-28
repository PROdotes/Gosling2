import pytest
from src.engine.models.spotify import SpotifyCredit
from src.services.mutation_coordinator import MutationCoordinator
from src.engine.routers.mutation_models import (
    MutationRequest,
    AddCreditItem,
    AddPublisherItem,
)


def _import_credits_bulk(db_path, song_id, credits, publishers):
    """Replaces old CatalogService.import_credits_bulk via MutationCoordinator."""
    add_items = [
        AddCreditItem(
            type="credit", song_id=song_id, name=c.name, role=c.role, id=c.identity_id
        )
        for c in credits
    ] + [
        AddPublisherItem(type="publisher", song_id=song_id, name=p) for p in publishers
    ]
    MutationCoordinator(db_path).apply(MutationRequest(add=add_items))


class TestCatalogBulkImport:
    def test_import_credits_bulk_success(self, catalog_service):
        """Verifies credit and publisher links are persisted and readable."""
        song_id = 2  # 'Get Lucky' - Daft Punk

        credits = [
            SpotifyCredit(name="Nile Rodgers", role="Guitar"),
            SpotifyCredit(name="Pharrell Williams", role="Vocals"),
        ]
        publishers = ["Sony/ATV", "Universal Music"]

        _import_credits_bulk(catalog_service._db_path, song_id, credits, publishers)

        song = catalog_service.get_song(song_id)

        names = {c.display_name for c in song.credits}
        assert "Nile Rodgers" in names, f"Expected 'Nile Rodgers' in {names}"
        assert "Pharrell Williams" in names, f"Expected 'Pharrell Williams' in {names}"

        nile_credit = [c for c in song.credits if c.display_name == "Nile Rodgers"][0]
        assert (
            nile_credit.role_name == "Guitar"
        ), f"Expected role 'Guitar', got {nile_credit.role_name}"

        pub_names = {p.name for p in song.publishers}
        assert "Sony/ATV" in pub_names, f"Expected 'Sony/ATV' in {pub_names}"
        assert (
            "Universal Music" in pub_names
        ), f"Expected 'Universal Music' in {pub_names}"

    def test_import_credits_bulk_invalid_song_raises(self, catalog_service):
        """LookupError raised for nonexistent song_id."""
        invalid_song_id = 9999

        with pytest.raises(Exception):
            _import_credits_bulk(
                catalog_service._db_path,
                invalid_song_id,
                [SpotifyCredit(name="A", role="B")],
                ["Pub"],
            )

        songs = catalog_service.search_songs_slim("")
        assert not any(
            s["SourceID"] == invalid_song_id for s in songs
        ), f"Song {invalid_song_id} should not exist"

    def test_import_credits_bulk_idempotency(self, catalog_service):
        """Re-importing the same credits doesn't create duplicates."""
        song_id = 2
        credits = [SpotifyCredit(name="Nile Rodgers", role="Guitar")]

        _import_credits_bulk(catalog_service._db_path, song_id, credits, [])
        count_1 = len(catalog_service.get_song(song_id).credits)

        _import_credits_bulk(catalog_service._db_path, song_id, credits, [])
        count_2 = len(catalog_service.get_song(song_id).credits)

        assert (
            count_1 == count_2
        ), f"Expected idempotent import, count changed from {count_1} to {count_2}"

    def test_import_credits_bulk_transactional_rollback(self, catalog_service):
        """Partial failure causes full rollback."""
        song_id = 2

        song_before = catalog_service.get_song(song_id)
        before_names = {c.display_name for c in song_before.credits}

        with pytest.raises(Exception):
            _import_credits_bulk(
                catalog_service._db_path,
                song_id,
                [SpotifyCredit(name="VALID NAME", role="Role")],
                [None],
            )

        song_after = catalog_service.get_song(song_id)
        after_names = {c.display_name for c in song_after.credits}
        assert "VALID NAME" not in after_names, "Transaction failed to rollback"
        assert (
            after_names == before_names
        ), f"Expected unchanged state, got diff: {after_names ^ before_names}"

    def test_import_credits_bulk_with_resolved_identity(self, catalog_service):
        """Provided identity_id is used for the credit (Truth-First)."""
        song_id = 1
        credits = [SpotifyCredit(name="The Drummer", role="Performer", identity_id=1)]

        _import_credits_bulk(catalog_service._db_path, song_id, credits, [])

        song = catalog_service.get_song(song_id)
        match = [c for c in song.credits if c.display_name == "The Drummer"][0]
        assert (
            match.identity_id == 1
        ), f"Expected identity 1 for 'The Drummer', got {match.identity_id}"
