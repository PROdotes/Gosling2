import pytest
from src.data.repositories.album_repository import AlbumRepository
from src.data.database import BaseRepository

def test_t91_assign_album(tmp_path):
    db_path = str(tmp_path / "t91_verify.db")
    BaseRepository(db_path)
    repo = AlbumRepository(db_path)
    
    # assign_album is supposed to handle T-91 logic
    # We need a source_id for the song
    with repo.get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO Types (TypeID, TypeName) VALUES (1, 'Song')")
        conn.execute("INSERT INTO MediaSources (SourcePath, MediaName, TypeID) VALUES ('test.mp3', 'Test', 1)")
        source_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # Also need Performer role
        conn.execute("INSERT OR IGNORE INTO Roles (RoleName) VALUES ('Performer')")

    # Create album using assign_album
    album = repo.assign_album(source_id, "T91 Assign Album", "Artist Alpha, Artist Beta")
    
    # Check if M2M links were created
    contributors = repo.get_contributors_for_album(album.album_id)
    
    print(f"\nContributors found: {[c.name for c in contributors]}")
    assert len(contributors) == 2, f"Expected 2 contributors for T-91, but found {len(contributors)}"

if __name__ == "__main__":
    pytest.main([__file__])
