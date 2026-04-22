import pytest
from pathlib import Path
from src.services.library_service import LibraryService
from src.services.edit_service import EditService
from src.engine import config
from tests.conftest import _connect

@pytest.fixture
def healing_env(populated_db, tmp_path, monkeypatch):
    """Sets up a controlled environment for testing self-healing moves."""
    library_root = tmp_path / "library"
    library_root.mkdir(parents=True, exist_ok=True)
    
    rules_path = tmp_path / "rules.json"
    # Rule for Pop includes {year}, Rule for Rock only {artist} - {title}
    rules_path.write_text(
        '{"routing_rules": ['
        '  {"match_genres": ["pop"], "target_path": "Pop/{year}/{artist} - {title}"},'
        '  {"match_genres": ["alt rock"], "target_path": "Rock/{artist} - {title}"}'
        '], "default_rule": "Other/{artist} - {title}"}'
    )
    
    # Initialize services with injected paths
    lib = LibraryService(populated_db, rules_path=rules_path, library_root=library_root)
    edit = EditService(populated_db, rules_path=rules_path, library_root=library_root)
    
    # Enable Auto-Move for the duration of these tests
    monkeypatch.setattr("src.engine.config.AUTO_MOVE_ON_APPROVE", True)
    
    return {
        "lib": lib,
        "edit": edit,
        "db": populated_db,
        "lib_root": library_root,
        "rules": rules_path
    }

def setup_song_at_path(db_path, song_id, target_path):
    """Manually places a file and updates the DB to simulate initial state."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(b"mp3 data")
    
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE MediaSources SET SourcePath = ?, ProcessingStatus = 0 WHERE SourceID = ?",
            (str(target_path), song_id)
        )
        conn.commit()

def test_trigger_on_title_change(healing_env):
    """Title change should trigger a physical file move."""
    lib, edit, lib_root = healing_env["lib"], healing_env["edit"], healing_env["lib_root"]
    
    # Setup initial state: Other/Nirvana - Smells Like Teen Spirit.mp3
    initial_path = lib_root / "Other" / "Nirvana - Smells Like Teen Spirit.mp3"
    setup_song_at_path(healing_env["db"], 1, initial_path)
    
    # Trigger Change
    edit.update_song_scalars(1, {"media_name": "Teen Spirit (Remix)"})
    
    # Verify Move
    new_path = lib_root / "Other" / "Nirvana - Teen Spirit (Remix).mp3"
    assert new_path.exists()
    assert not initial_path.exists()

def test_trigger_on_primary_genre_change(healing_env):
    """Changing primary genre from Rock to Pop should move the file to Pop/Year/ directory."""
    lib, edit, lib_root = healing_env["lib"], healing_env["edit"], healing_env["lib_root"]
    
    initial_path = lib_root / "Other" / "Nirvana - Smells Like Teen Spirit.mp3"
    setup_song_at_path(healing_env["db"], 1, initial_path)
    
    # Change Primary Genre to Pop (Alt Rock ID 6 in populated_db)
    with _connect(healing_env["db"]) as conn:
        # First ensure Tag 6 is linked to Song 1
        conn.execute("INSERT OR IGNORE INTO MediaSourceTags (SourceID, TagID, IsPrimary) VALUES (1, 6, 0)")
        # Set Alt Rock (ID 6) as primary
        conn.execute("UPDATE MediaSourceTags SET IsPrimary = 0 WHERE SourceID = 1")
        conn.execute("UPDATE MediaSourceTags SET IsPrimary = 1 WHERE SourceID = 1 AND TagID = 6")
        conn.commit()
    
    # Hydrate to trigger move
    song = lib.get_song(1)
    
    # Verify move to 'Rock' path (matching 'alt rock' rule)
    new_path = lib_root / "Rock" / "Nirvana - Smells Like Teen Spirit.mp3"
    assert new_path.exists()
    assert not initial_path.exists()

def test_no_trigger_on_composer_change(healing_env):
    """Changing a composer (non-placeholder) should NOT trigger a file move."""
    lib, edit, lib_root = healing_env["lib"], healing_env["edit"], healing_env["lib_root"]
    
    initial_path = lib_root / "Other" / "Nirvana - Smells Like Teen Spirit.mp3"
    setup_song_at_path(healing_env["db"], 1, initial_path)
    
    # Add a Composer credit
    edit.add_song_credit(1, "Butch Vig", role_name="Composer")
    
    # Verify NO move
    assert initial_path.exists()
    assert len(list(lib_root.rglob("*.mp3"))) == 1

def test_trigger_on_year_change_for_pop(healing_env):
    """Year change should trigger move ONLY if year is in the routing rule (like Pop)."""
    lib, edit, lib_root = healing_env["lib"], healing_env["edit"], healing_env["lib_root"]
    
    # Setup as Pop: Create tag 'Pop' if not exists, set as primary
    initial_path = lib_root / "Pop" / "1991" / "Nirvana - Smells Like Teen Spirit.mp3"
    setup_song_at_path(healing_env["db"], 1, initial_path)
    with _connect(healing_env["db"]) as conn:
        # Create Pop tag (ID 20 maybe? Or just let repo handle it)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO Tags (TagName, TagCategory) VALUES ('Pop', 'Genre')")
        pop_id = cursor.execute("SELECT TagID FROM Tags WHERE TagName = 'Pop'").fetchone()[0]
        
        conn.execute("UPDATE MediaSourceTags SET IsPrimary = 0 WHERE SourceID = 1")
        conn.execute("INSERT OR REPLACE INTO MediaSourceTags (SourceID, TagID, IsPrimary) VALUES (1, ?, 1)", (pop_id,))
        conn.commit()
    
    # Change Year
    edit.update_song_scalars(1, {"year": 2024})
    
    # Verify Move (Change Rock to Pop path)
    new_path = lib_root / "Pop" / "2024" / "Nirvana - Smells Like Teen Spirit.mp3"
    assert new_path.exists()
    assert not initial_path.exists()
