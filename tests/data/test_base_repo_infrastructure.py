from src.data.base_repository import BaseRepository


class TestBaseRepoInfrastructure:
    """Verifies the core database connection infrastructure."""

    def test_get_connection_enables_foreign_keys(self, empty_db):
        repo = BaseRepository(empty_db)
        conn = repo.get_connection()
        try:
            # Query the PRAGMA directly
            res = conn.execute("PRAGMA foreign_keys").fetchone()
            # 1 = ON, 0 = OFF
            assert res[0] == 1, f"Expected foreign_keys=1, got {res[0]}"
        finally:
            conn.close()

    def test_audiohash_is_unique(self, empty_db):
        repo = BaseRepository(empty_db)
        conn = repo.get_connection()
        try:
            # Check for UNIQUE index on AudioHash
            indices = conn.execute("PRAGMA index_list(MediaSources)").fetchall()
            # Find an index that is UNIQUE and maps to AudioHash
            found_unique_hash = False
            for idx in indices:
                idx_name = idx[1]
                is_unique = idx[2]
                if is_unique:
                    # Check columns for this index
                    cols = conn.execute(f"PRAGMA index_info({idx_name})").fetchall()
                    if any(col[2] == "AudioHash" for col in cols):
                        found_unique_hash = True
                        break

            assert found_unique_hash, (
                "AudioHash column does not have a UNIQUE constraint/index"
            )
        finally:
            conn.close()

    def test_get_connection_registers_custom_collation(self, empty_db):
        repo = BaseRepository(empty_db)
        conn = repo.get_connection()
        try:
            # Verify the collation is registered by using it in a query
            # (If not registered, this will raise a sqlite3.Error)
            conn.execute("SELECT 'A' == 'a' COLLATE UTF8_NOCASE")
        finally:
            conn.close()
