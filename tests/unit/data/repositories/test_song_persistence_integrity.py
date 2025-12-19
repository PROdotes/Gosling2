import pytest
import sqlite3
from unittest.mock import MagicMock, patch
from src.data.repositories.song_repository import SongRepository
from src.data.repositories.base_repository import BaseRepository
from src.data.models.song import Song

def test_repository_update_fields_coverage(tmp_path):
    """
    Persistence Integrity Test (Update):
    Ensures that SongRepository.update() includes ALL mutable columns from the 'MediaSources' and 'Songs' tables.
    """
    # 1. Get Actual DB Columns (Source of Truth)
    db_path = tmp_path / "test_persist.db"
    BaseRepository(str(db_path)) 
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Check MediaSources
        cursor.execute("PRAGMA table_info(MediaSources)")
        ms_cols = {row[1] for row in cursor.fetchall() if row[1] not in ("SourceID", "Source", "TypeID", "IsActive", "Notes")}
        
        # Check Songs
        cursor.execute("PRAGMA table_info(Songs)")
        s_cols = {row[1] for row in cursor.fetchall() if row[1] not in ("SourceID")}
    
    # Identify Mutable Columns
    # MediaSources: Name, Duration
    # Songs: TempoBPM, RecordingYear, ISRC, IsDone, Groups
    mutable_columns = ms_cols.union(s_cols)
    
    # 2. Capture Actual SQL execution
    with patch.object(BaseRepository, 'get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        repo = SongRepository(str(db_path))
        dummy_song = Song(source_id=1, source="t", name="t", duration=0, bpm=0, is_done=False)
        
        repo.update(dummy_song)
        
        # 3. Analyze Executed SQL
        all_sql = " ".join(call[0][0] for call in mock_cursor.execute.call_args_list)
        
        # 4. Verify Column Presence
        missing_updates = []
        for col in mutable_columns:
            if col not in all_sql:
                missing_updates.append(col)
                
        assert not missing_updates, \
            f"SongRepository.update() is NOT updating these Database columns: {missing_updates}. " \
            "You added a column to the DB but forgot to save it in repo.update()!"

def test_repository_insert_fields_coverage(tmp_path):
    """
    Persistence Integrity Test (Insert):
    Ensures that SongRepository.insert() handles at least the REQUIRED columns.
    """
    db_path = tmp_path / "test_persist_insert.db"
    BaseRepository(str(db_path)) 
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Check MediaSources
        cursor.execute("PRAGMA table_info(MediaSources)")
        ms_required = {row[1] for row in cursor.fetchall() if row[3] == 1 and row[4] is None and row[5] == 0}
        
    with patch.object(BaseRepository, 'get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        repo = SongRepository(str(db_path))
        repo.insert("some/path.mp3")
        
        all_sql = " ".join(call[0][0] for call in mock_cursor.execute.call_args_list)
        
        missing_inserts = [col for col in ms_required if col not in all_sql]
        assert not missing_inserts, \
            f"SongRepository.insert() is skipping REQUIRED columns: {missing_inserts}. " \
            "These columns are NOT NULL and have no default; insert will fail!"
