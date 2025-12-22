import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.repositories.song_repository import SongRepository

"""
Fixture Injector for Test Songs.
Reads `tests/fixtures/test_songs.json` and populates the database.

JSON Schema (All fields strictly required by current logic):
[
  {
    "path": "C:\\Path\\To.mp3",       # Unique Key (Required)
    "title": "Song Title",            # (Required)
    "artist": "Artist Name",          # (Required) -> Maps to unified_artist
    "year": 1999,                     # (Required) -> Maps to recording_year
    "album": "Album Name"             # (Required) -> Triggers Album Sync
  }
]
"""

def inject():
    fixture_path = project_root / 'tests/fixtures/test_songs.json'
    with open(fixture_path, 'r') as f:
        songs_data = json.load(f)

    repo = SongRepository()
    
    print(f"Loaded {len(songs_data)} songs from fixture.")
    
    count = 0
    seen_paths = set()  # Track processed songs for M2M support
    
    for data in songs_data:
        # Normalize path
        raw_path = data['path']
        path = os.path.normcase(os.path.abspath(raw_path))
        
        # 1. Clean old (only on first encounter of this path)
        if path not in seen_paths:
            with repo.get_connection() as conn:
                conn.execute("DELETE FROM MediaSources WHERE Source = ?", (path,))
            
            # 2. Insert
            source_id = repo.insert(path)
            if not source_id:
                print(f"Failed to insert {path}")
                continue
            seen_paths.add(path)
        else:
            # Already exists, just get it
            song = repo.get_by_path(path)
            if not song:
                print(f"Failed to find existing {path}")
                continue
            
        # 3. Update Metadata
        song = repo.get_by_path(path)
        song.title = data['title']
        song.unified_artist = data['artist'] # Note: Logic uses Contributors, this helps simple display
        song.recording_year = data['year']
        song.album = data['album']
        song.publisher = data.get('publisher')  # Optional
        song.genre = data.get('genre') # Optional
        
        # 4. Save (Triggers _sync_album and _sync_publisher)
        success = repo.update(song)
        if success:
            pub_str = f" | Publisher: {song.publisher}" if song.publisher else ""
            print(f"[OK] Injected: {song.title} -> Album: {song.album}{pub_str}")
            count += 1
        else:
            print(f"[FAIL] Failed to update: {song.title}")

    print(f"\n--- Injection Complete ({count}/{len(songs_data)}) ---")
    
    # Report on Albums
    with repo.get_connection() as conn:
        cursor = conn.execute("SELECT AlbumID, Title, ReleaseYear FROM Albums")
        albums = cursor.fetchall()
        print(f"\nCreated {len(albums)} Albums in DB:")
        for alb in albums:
            # Count songs
            c2 = conn.execute("SELECT COUNT(*) FROM SongAlbums WHERE AlbumID=?", (alb[0],))
            song_count = c2.fetchone()[0]
            print(f"[ALBUM] ID {alb[0]}: '{alb[1]}' ({alb[2]}) - {song_count} Songs")

if __name__ == "__main__":
    inject()
