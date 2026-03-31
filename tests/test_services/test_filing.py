import pytest
from pathlib import Path
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
        id=1, media_name="Moja Pjesma", source_path="temp/staging/test.mp3", duration_s=180.0, year=2024,
        processing_status=0, # Reviewed
        credits=[SongCredit(credit_id=1, source_id=1, name_id=1, role_id=1, role_name="Performer", display_name="Oliver Dragojević", is_primary=True)],
        tags=[Tag(id=10, name="Pop", category="Genre", is_primary=True)]
    )
    target = filing_service.evaluate_routing(song)
    assert "Oliver Dragojevic" in str(target)
    assert target.isascii()

def test_evaluate_routing_missing_metadata_fails(filing_service):
    # This scenario technically shouldn't happen for status 0, but verified anyway
    song_no_artist = Song(
        id=2, media_name="Title", source_path="test.mp3", duration_s=100.0, year=2024,
        processing_status=0,
        credits=[], # No performers
        tags=[Tag(id=10, name="Pop", category="Genre", is_primary=True)]
    )
    with pytest.raises(ValueError, match="missing Performer credits"):
        filing_service.evaluate_routing(song_no_artist)

def test_move_song_to_library_collision_fails(filing_service, tmp_path):
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    source_file = staging_dir / "test.mp3"
    source_file.write_text("content")
    library_root = tmp_path / "library"
    library_root.mkdir()
    
    # Pre-create target file
    (library_root / "2024").mkdir()
    target_file = library_root / "2024" / "Artist - Title.mp3"
    target_file.write_text("existing")
    
    song = Song(
        id=1, media_name="Title", source_path=str(source_file), duration_s=180.0, year=2024,
        processing_status=0,
        credits=[SongCredit(credit_id=1, source_id=1, name_id=1, role_id=1, role_name="Performer", display_name="Artist", is_primary=True)],
        tags=[Tag(id=10, name="Pop", category="Genre", is_primary=True)]
    )
    
    with pytest.raises(FileExistsError, match="Target path already exists"):
        filing_service.move_to_library(song, library_root)
    
    # Verify both files still exist (No deletion)
    assert source_file.exists()
    assert target_file.exists()
