import pytest
import sqlite3
import os
from src.data.database import BaseRepository

def test_database_column_naming_alignment():
    """
    STRICT ALIGNMENT TEST:
    Verifies that the database schema matches the mandatory naming conventions in DATABASE.md.
    
    Source of Truth: DATABASE.md
    - Contributors -> ContributorName
    - Roles -> RoleName
    - Types -> TypeName
    """
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        repo = BaseRepository(db_path)
        with repo.get_connection() as conn:
            # Schema already ensured by __init__ -> _ensure_schema
            cursor = conn.cursor()
            
            # 1. Check Contributors
            cursor.execute("PRAGMA table_info(Contributors)")
            contributor_cols = {row[1] for row in cursor.fetchall()}
            assert "ContributorName" in contributor_cols, f"Contributors table missing 'ContributorName'. Found: {contributor_cols}"
            assert "Name" not in contributor_cols, "Contributors table using generic 'Name' instead of 'ContributorName'"
            
            # 2. Check Roles
            cursor.execute("PRAGMA table_info(Roles)")
            role_cols = {row[1] for row in cursor.fetchall()}
            assert "RoleName" in role_cols, f"Roles table missing 'RoleName'. Found: {role_cols}"
            assert "Name" not in role_cols, "Roles table using generic 'Name' instead of 'RoleName'"
            
            # 3. Check Types (Verification)
            cursor.execute("PRAGMA table_info(Types)")
            type_cols = {row[1] for row in cursor.fetchall()}
            assert "TypeName" in type_cols, f"Types table missing 'TypeName'. Found: {type_cols}"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
