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
            "RecordingYear": "Year",
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
            
            pytest.fail(f"SongRepository.get_all() is missing DB Column '{db_col}'! "
                        f"Update the SQL query to include it.")

def test_strict_table_whitelist(tmp_path):
    """
    STRICT Table Whitelisting:
    Ensures that the SongRepository accounts for EVERY table in the database.
    
    If a developer adds a table (e.g. 'Genres'), this test will FAIL until 
    that table is explicitly added to the Repository's KNOWN_TABLES list.
    """
    db_path = tmp_path / "test_repo_schema_tables.db"
    repo = SongRepository(str(db_path))
    
    with repo.get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch ALL Tables in physical DB
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        actual_tables = {row[0] for row in cursor.fetchall()}
        
        # 2. Define Repository's Known Tables
        # These are the tables the repository claims to manage/interact with.
        known_tables = {
            "Files",
            "Contributors",
            "Roles",
            "FileContributorRoles",
            "GroupMembers"
        }
        
        # 3. Assert Exact Match
        # Any extra table in DB means "I don't know this table, thus I might break integration."
        extra_tables = actual_tables - known_tables
        if extra_tables:
            pytest.fail(f"STRICT CHECK FAILED: Unknown tables detected in database: {extra_tables}. "
                        f"The SongRepository must explicitly whitelist these tables to prove it handles them.")
        
        # Verify we aren't missing expected tables either (which would be a fundamental breakage)
        missing_tables = known_tables - actual_tables
        assert not missing_tables, f"Database is missing expected tables: {missing_tables}"
