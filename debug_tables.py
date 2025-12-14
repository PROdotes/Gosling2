from src.data.repositories.base_repository import BaseRepository

repo = BaseRepository(":memory:")
with repo.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Tables found:", [row[0] for row in tables])
