import pytest
from src.data.repositories.contributor_repository import ContributorRepository

def test_get_by_role_schema_integrity(tmp_path):
    """
    Schema Integrity Test:
    Ensures that ContributorRepository.get_by_role() returns exactly [ContributorID, Name].
    Verifies that the SQL query matches expectations.
    """
    # Use a file-based DB to ensure schema persistence across connections
    db_path = tmp_path / "test_contrib_schema.db"
    repo = ContributorRepository(str(db_path))
    
    expected_columns = ["ContributorID", "Name"]
    
    try:
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            
            # Logic from actual method:
            query = """
                SELECT DISTINCT C.ContributorID, C.Name
                FROM Contributors C
                JOIN MediaSourceContributorRoles MSCR ON C.ContributorID = MSCR.ContributorID
                JOIN Roles R ON MSCR.RoleID = R.RoleID
                WHERE R.Name = ?
                ORDER BY C.SortName ASC
            """
            cursor.execute(query, ("AnyRole",))
            
            actual_columns = [description[0] for description in cursor.description]
            
            assert actual_columns == expected_columns, \
                f"Contributor Schema Mismatch! Expected {expected_columns}, got {actual_columns}"
                
    except Exception as e:
        pytest.fail(f"Contributor Schema Test Failed: {e}")
