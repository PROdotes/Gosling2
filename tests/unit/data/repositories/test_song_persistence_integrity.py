import pytest
import sqlite3
from unittest.mock import MagicMock, patch
from src.data.repositories.song_repository import SongRepository
from src.data.repositories.base_repository import BaseRepository
from src.data.models.song import Song

def test_repository_update_fields_coverage(tmp_path):
    """
    Persistence Integrity Test (Update):
    Ensures that SongRepository.update() includes ALL mutable columns from the 'Files' table in its SQL.
    
    If you add 'ReleaseYear' to the DB, you MUST add it to the UPDATE statement in existing code,
    otherwise this test fails, preventing "Data Amnesia" (saving success but data lost).
    """
    # 1. Get Actual DB Columns (Source of Truth)
    db_path = tmp_path / "test_persist.db"
    # Create DB using BaseRepository to get fresh schema
    BaseRepository(str(db_path)) 
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Files)")
        columns_info = cursor.fetchall() # (cid, name, type, notnull, dflt_value, pk)
    
    # Identify Mutable Columns (All except PK 'FileID')
    # We might exclude 'Path' if we consider it immutable after insert (Logic decision).
    # Current Repo implementation allows Path update? No, it only updates Title, Duration, BPM.
    # Path is usually fixed. Let's assume Path is NOT mutable via update() for now 
    # (or if it is, it should be in SQL).
    # Repo.update() SQL: "UPDATE Files SET Title = ?, Duration = ?, TempoBPM = ? WHERE FileID = ?"
    # So Path is NOT there.
    
    mutable_columns = {row[1] for row in columns_info if row[1] not in ("FileID", "Path")}
    
    # 2. Capture Actual SQL execution
    # We mock the connection inside SongRepository
    with patch.object(BaseRepository, 'get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        repo = SongRepository(str(db_path))
        dummy_song = Song(file_id=1, path="t", title="t", duration=0, bpm=0)
        
        repo.update(dummy_song)
        
        # 3. Analyze Executed SQL
        # We look for the UPDATE statement
        update_sql = ""
        for call in mock_cursor.execute.call_args_list:
            sql = call[0][0]
            if "UPDATE Files" in sql:
                update_sql = sql
                break
        
        assert update_sql, "SongRepository.update() did not execute an 'UPDATE Files' statement!"
        
        # 4. Verify Column Presence
        # The SQL should look like "UPDATE Files SET Col1=?, Col2=..."
        # We check if every mutable column name appears in the SQL string.
        # This is a basic string check, but effective.
        
        missing_updates = []
        for col in mutable_columns:
            # We check if "ColumnName =" or "ColumnName=" is in the string usually
            # But just checking the name is fairly safe given the context.
            if col not in update_sql:
                # Special check for aliased mapping if any (TempoBPM vs BPM)
                # But here we are checking PHYSICAL DB COLUMNS vs SQL.
                # The SQL MUST use the physical name "TempoBPM".
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
        cursor.execute("PRAGMA table_info(Files)")
        columns_info = cursor.fetchall()
        
    # Validating that we provide values for all NOT NULL columns that don't have defaults
    required_columns = {row[1] for row in columns_info if row[3] == 1 and row[4] is None and row[5] == 0}
    # row[3]=notnull, row[4]=dflt_value, row[5]=pk
    
    with patch.object(BaseRepository, 'get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        repo = SongRepository(str(db_path))
        repo.insert("some/path.mp3")
        
        insert_sql = ""
        for call in mock_cursor.execute.call_args_list:
            sql = call[0][0]
            if "INSERT" in sql and "Files" in sql:
                insert_sql = sql
                break
                
        assert insert_sql, "Repo.insert() did not execute INSERT statement!"
        
        missing_inserts = [col for col in required_columns if col not in insert_sql]
        assert not missing_inserts, \
            f"SongRepository.insert() is skipping REQUIRED columns: {missing_inserts}. " \
            "These columns are NOT NULL and have no default; insert will fail!"
