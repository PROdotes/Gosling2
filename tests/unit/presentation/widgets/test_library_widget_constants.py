import pytest
from src.presentation.widgets.library_widget import LibraryWidget
from src.data.repositories.song_repository import SongRepository

def test_library_widget_constants_alignment(tmp_path):
    """
    Library Widget Schema Integrity:
    Ensures that the column constants in LibraryWidget (COL_DURATION, etc.)
    align EXACTLY with the column order returned by SongRepository.
    
    If Developer adds a column to Repo, the indices shift. 
    This test alerts them to update the Widget constants.
    """
    # 1. Get Repo Headers (Source of Truth)
    db_path = tmp_path / "test_const_align.db"
    repo = SongRepository(str(db_path))
    # We rely on an empty DB returning headers correctly
    headers, _ = repo.get_all()
    
    assert headers, "Repo returned no headers! Fix Repo test first."
    
    # 2. Check Constants
    # We inspect the class attributes directly
    
    # Duration
    assert "Duration" in headers, "Duration column missing from Repo?"
    expected_duration_idx = headers.index("Duration")
    assert LibraryWidget.COL_DURATION == expected_duration_idx, \
        f"LibraryWidget.COL_DURATION mismatch! Expected {expected_duration_idx}, got {LibraryWidget.COL_DURATION}. " \
        "Repository column order changed. Update LibraryWidget constants."
        
    # BPM
    assert "BPM" in headers, "BPM column missing from Repo?"
    expected_bpm_idx = headers.index("BPM")
    assert LibraryWidget.COL_BPM == expected_bpm_idx, \
        f"LibraryWidget.COL_BPM mismatch! Expected {expected_bpm_idx}, got {LibraryWidget.COL_BPM}. " \
        "Repository column order changed. Update LibraryWidget constants."
        
    # FileID
    assert "FileID" in headers, "FileID column missing from Repo?"
    expected_file_id_idx = headers.index("FileID")
    assert LibraryWidget.COL_FILE_ID == expected_file_id_idx, \
        f"LibraryWidget.COL_FILE_ID mismatch! Expected {expected_file_id_idx}, got {LibraryWidget.COL_FILE_ID}. " \
        "Repository column order changed. Update LibraryWidget constants."

    # Future Alerting:
    # If developer adds "RecordingYear" at index X, they might shift Duration.
    # This test guarantees they notice.
