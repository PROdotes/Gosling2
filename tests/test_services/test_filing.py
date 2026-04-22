import pytest
from src.services.filing_service import FilingService
from src.models.domain import Song, SongCredit, Tag


@pytest.fixture
def filing_service(tmp_path):
    rules_path = tmp_path / "rules.json"
    rules_path.write_text("""
    {
        "routing_rules": [
            {
                "match_genres": ["pop"],
                "target_path": "{year}/{artist} - {title}"
            }
        ],
        "default_rule": "{genre}/{year}/{artist} - {title}"
    }
    """)
    return FilingService(rules_path=rules_path)


def test_evaluate_routing_basic(filing_service):
    song = Song(
        id=1,
        media_name="Moja Pjesma",
        source_path="temp/staging/test.mp3",
        duration_s=180.0,
        year=2024,
        processing_status=0,  # Reviewed
        credits=[
            SongCredit(
                credit_id=1,
                source_id=1,
                name_id=1,
                role_id=1,
                role_name="Performer",
                display_name="Oliver Dragojević",
                is_primary=True,
            )
        ],
        tags=[Tag(id=10, name="Pop", category="Genre", is_primary=True)],
    )
    target = filing_service.evaluate_routing(song)
    assert "Oliver Dragojevic" in str(target)
    assert str(target).isascii()


def test_evaluate_routing_missing_metadata_fails(filing_service):
    # This scenario technically shouldn't happen for status 0, but verified anyway
    song_no_artist = Song(
        id=2,
        media_name="Title",
        source_path="test.mp3",
        duration_s=100.0,
        year=2024,
        processing_status=0,
        credits=[],  # No performers
        tags=[Tag(id=10, name="Pop", category="Genre", is_primary=True)],
    )
    with pytest.raises(ValueError, match="missing Performer credits"):
        filing_service.evaluate_routing(song_no_artist)


def test_move_song_to_library_collision_fails(filing_service, tmp_path):
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir(exist_ok=True)
    source_file = staging_dir / "test.mp3"
    source_file.write_text("content")
    library_root = tmp_path / "library"
    library_root.mkdir(exist_ok=True)

    # Pre-create target file
    (library_root / "2024").mkdir(exist_ok=True)
    target_file = library_root / "2024" / "Artist - Title.mp3"
    target_file.write_text("existing")

    song = Song(
        id=1,
        media_name="Title",
        source_path=str(source_file),
        duration_s=180.0,
        year=2024,
        processing_status=0,
        credits=[
            SongCredit(
                credit_id=1,
                source_id=1,
                name_id=1,
                role_id=1,
                role_name="Performer",
                display_name="Artist",
                is_primary=True,
            )
        ],
        tags=[Tag(id=10, name="Pop", category="Genre", is_primary=True)],
    )

    with pytest.raises(FileExistsError, match="Target path already exists"):
        filing_service.copy_to_library(song, library_root)

    # Verify both files still exist (No deletion)
    assert source_file.exists()
    assert target_file.exists()


def _make_song(source_path: str) -> object:
    """Minimal Song for filing tests."""
    return Song(
        id=99,
        media_name="Title",
        source_path=source_path,
        duration_s=180.0,
        year=2024,
        processing_status=0,
        credits=[
            SongCredit(
                credit_id=1,
                source_id=1,
                name_id=1,
                role_id=1,
                role_name="Performer",
                display_name="Artist",
                is_primary=True,
            )
        ],
        tags=[Tag(id=10, name="Pop", category="Genre", is_primary=True)],
    )


class TestCopyToLibraryInPlace:
    """copy_to_library when source IS already the target (in-place ingestion path)."""

    def test_source_equals_target_returns_path_without_error(self, filing_service, tmp_path):
        """When source_path resolves to the same inode as target, return target without raising."""
        library_root = tmp_path / "library"
        (library_root / "2024").mkdir(parents=True)
        existing_file = library_root / "2024" / "Artist - Title.mp3"
        existing_file.write_bytes(b"real audio data")

        song = _make_song(str(existing_file))

        result = filing_service.copy_to_library(song, library_root)

        assert result == existing_file, (
            f"Expected target path {existing_file}, got {result}"
        )

    def test_source_equals_target_file_still_exists_after_call(self, filing_service, tmp_path):
        """Original file must survive copy_to_library when source IS the target — no deletion."""
        library_root = tmp_path / "library"
        (library_root / "2024").mkdir(parents=True)
        existing_file = library_root / "2024" / "Artist - Title.mp3"
        existing_file.write_bytes(b"original content do not delete")

        song = _make_song(str(existing_file))
        filing_service.copy_to_library(song, library_root)

        assert existing_file.exists(), "Original file was deleted during in-place copy_to_library — this is a critical regression"
        assert existing_file.read_bytes() == b"original content do not delete", (
            "File contents were modified during in-place copy_to_library"
        )

    def test_different_source_and_target_still_copies(self, filing_service, tmp_path):
        """When source != target, the normal copy path still works correctly."""
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir(exist_ok=True)
        source_file = staging_dir / "some_uuid_Artist - Title.mp3"
        source_file.write_bytes(b"staged content")

        library_root = tmp_path / "library"
        library_root.mkdir()

        song = _make_song(str(source_file))
        result = filing_service.copy_to_library(song, library_root)

        assert result.exists(), f"Expected file to be copied to {result}, but it does not exist"
        assert result.read_bytes() == b"staged content", "Copied file content does not match source"
        assert source_file.exists(), "Source staging file was deleted during copy — should only be unlinked by EditService"

