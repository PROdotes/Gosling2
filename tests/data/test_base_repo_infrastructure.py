from src.data.base_repository import BaseRepository


class TestBaseRepoInfrastructure:
    """Verifies the core database connection infrastructure."""

    def test_get_connection_enables_foreign_keys(self, empty_db):
        repo = BaseRepository(empty_db)
        with repo._get_connection() as conn:
            # Query the PRAGMA directly
            res = conn.execute("PRAGMA foreign_keys").fetchone()
            # 1 = ON, 0 = OFF
            assert res[0] == 1, f"Expected foreign_keys=1, got {res[0]}"

    def test_get_connection_creates_audiohash_index(self, empty_db):
        repo = BaseRepository(empty_db)
        with repo._get_connection() as conn:
            # Check the sqlite_master for the index
            query = "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_mediasources_audiohash'"
            res = conn.execute(query).fetchone()
            assert (
                res is not None
            ), "Index 'idx_mediasources_audiohash' was not created automatically"
            assert (
                res[0] == "idx_mediasources_audiohash"
            ), f"Expected index name 'idx_mediasources_audiohash', got {res[0]}"

    def test_get_connection_registers_custom_collation(self, empty_db):
        repo = BaseRepository(empty_db)
        with repo._get_connection() as conn:
            # Verify the collation is registered by using it in a query
            # (If not registered, this will raise a sqlite3.Error)
            conn.execute("SELECT 'A' == 'a' COLLATE UTF8_NOCASE")
