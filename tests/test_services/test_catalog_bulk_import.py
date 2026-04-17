import pytest
from src.engine.models.spotify import SpotifyCredit


class TestCatalogBulkImport:
    def test_import_credits_bulk_success(self, catalog_service):
        """Rule 155: Verifies service orchestration and hydration."""
        song_id = 2  # 'Get Lucky' - Daft Punk

        # Test data: 1 new artist, 1 existing artist, new role.
        credits = [
            SpotifyCredit(name="Nile Rodgers", role="Guitar"),
            SpotifyCredit(name="Pharrell Williams", role="Vocals"),
        ]
        publishers = ["Sony/ATV", "Universal Music"]

        # Act
        catalog_service.import_credits_bulk(song_id, credits, publishers)

        # Assert - Verify hydration and persistence via Service read methods
        song = catalog_service.get_song(song_id)

        # Verify credits: check exact names and roles
        names = {c.display_name for c in song.credits}
        assert "Nile Rodgers" in names, f"Expected 'Nile Rodgers' in {names}"
        assert "Pharrell Williams" in names, f"Expected 'Pharrell Williams' in {names}"

        # Verify exhaustive fields for a single credit
        nile_credit = [c for c in song.credits if c.display_name == "Nile Rodgers"][0]
        assert nile_credit.role_name == "Guitar", (
            f"Expected role 'Guitar', got {nile_credit.role_name}"
        )

        # Verify publishers
        pub_names = {p.name for p in song.publishers}
        assert "Sony/ATV" in pub_names, f"Expected 'Sony/ATV' in {pub_names}"
        assert "Universal Music" in pub_names, (
            f"Expected 'Universal Music' in {pub_names}"
        )

    def test_import_credits_bulk_invalid_song_raises(self, catalog_service):
        """Rule 83: Assert state after the error."""
        invalid_song_id = 9999

        with pytest.raises(LookupError):
            catalog_service.import_credits_bulk(
                invalid_song_id, [SpotifyCredit(name="A", role="B")], ["Pub"]
            )

        # Verify record does not exist
        songs = catalog_service.search_songs_slim("")  # Get all
        assert not any(s["SourceID"] == invalid_song_id for s in songs), (
            f"Song {invalid_song_id} should not exist"
        )

    def test_import_credits_bulk_idempotency(self, catalog_service):
        """Verifies that re-importing the same text doesn't create duplicate links."""
        song_id = 2
        credits = [SpotifyCredit(name="Nile Rodgers", role="Guitar")]

        # First import
        catalog_service.import_credits_bulk(song_id, credits, [])
        song_mid = catalog_service.get_song(song_id)
        count_1 = len(song_mid.credits)

        # Second import (same)
        catalog_service.import_credits_bulk(song_id, credits, [])
        song_final = catalog_service.get_song(song_id)
        count_2 = len(song_final.credits)

        assert count_1 == count_2, (
            f"Expected idempotent import, but credit count changed from {count_1} to {count_2}"
        )

    def test_import_credits_bulk_transactional_rollback(self, catalog_service):
        """Rule 94: Verifies partial failure causes full rollback."""
        song_id = 2

        # Get baseline
        song_before = catalog_service.get_song(song_id)
        before_names = {c.display_name for c in song_before.credits}

        with pytest.raises(Exception):
            catalog_service.import_credits_bulk(
                song_id, [SpotifyCredit(name="VALID NAME", role="Role")], [None]
            )

        # Verify rollback: "VALID NAME" should NOT be in the DB
        song_after = catalog_service.get_song(song_id)
        after_names = {c.display_name for c in song_after.credits}
        assert "VALID NAME" not in after_names, (
            "Transaction failed to rollback: 'VALID NAME' was created despite trailing failure"
        )
        assert after_names == before_names, (
            f"Expected state to be identical to baseline, but it changed: {after_names ^ before_names}"
        )

    def test_import_credits_bulk_with_resolved_identity(self, catalog_service):
        """Service should use provided identity_id for credits (Truth-First)."""
        song_id = 1  # Smells Like Teen Spirit
        # David Grohl is ID 1 in populated_db
        credits = [SpotifyCredit(name="The Drummer", role="Performer", identity_id=1)]

        # Act
        catalog_service.import_credits_bulk(song_id, credits, [])

        # Assert
        song = catalog_service.get_song(song_id)
        match = [c for c in song.credits if c.display_name == "The Drummer"][0]
        assert match.identity_id == 1, (
            f"Expected identity 1 for 'The Drummer', got {match.identity_id}"
        )
