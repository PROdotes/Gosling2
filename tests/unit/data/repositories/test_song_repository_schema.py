import pytest
from src.data.repositories.song_repository import SongRepository

def test_get_all_schema_integrity(tmp_path):
    """
    Schema Integrity Test:
    Ensures that SongRepository.get_all() retrieves ALL relevant data from the 'Files' table.
    
    If a developer adds a column to 'Files' (e.g., RecordingYear), this test verifies 
    that it is effectively exposed by the Repository (either directly or via known mapping).
    """
    # Use a file-based DB to ensure PRAGMA works
    db_path = tmp_path / "test_repo_schema.db"
    repo = SongRepository(str(db_path))
    
    with repo.get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Get Physical DB Columns from 'Files'
        cursor.execute("PRAGMA table_info(Files)")
        db_columns_info = cursor.fetchall()
        db_columns = {row[1] for row in db_columns_info}
        
        # 2. Get Repository Query Columns
        # We execute the ACTUAL query from the class (using the same logic as the class)
        # Note: We duplicate the query here to statically analyze it, or we could call the method?
        # Calling the method on empty DB is fine, returns empty data but we can inspect headers?
        # Repo.get_all() returns (headers, data).
        repo_headers, _ = repo.get_all()
        repo_columns_set = set(repo_headers)
        
        # 3. Define Known Mappings (DB Column -> Repo Header)
        # Some columns are renamed in the view.
        column_mapping = {
            "TempoBPM": "BPM", 
            # Relationships are complex, but for 'Files' table columns:
            "FileID": "FileID",
            "Path": "Path",
            "Title": "Title", 
            "Duration": "Duration",
            # If RecordingYear is added, it maps to "RecordingYear" (default) or needs mapping.
        }
        
        # 4. Verify Coverage
        # Every column in Files table MUST be represented in Repo Headers
        for db_col in db_columns:
            # Check direct match
            if db_col in repo_columns_set:
                continue
                
            # Check mapped match
            if db_col in column_mapping:
                mapped_name = column_mapping[db_col]
                if mapped_name in repo_columns_set:
                    continue
            
            # If we reach here, the DB column is NOT returned by the Repository
            pytest.fail(f"SongRepository.get_all() is missing DB Column '{db_col}'! "
                        f"Update the SQL query to include it.")
