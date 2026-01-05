
import sys
import os
import sqlite3
import datetime
import shutil

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.database import BaseRepository
from src.data.repositories.song_repository import SongRepository
from src.data.repositories.audit_repository import AuditRepository
from src.business.services.audit_service import AuditService
from src.data.models.song import Song

DB_PATH = "audit_test.db"

def setup():
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except PermissionError:
            print(f"Warning: Could not delete {DB_PATH}, might be in use.")
    
    # Initialize Schema
    repo = BaseRepository(DB_PATH)
    print(f"Database initialized at {DB_PATH}")
    
    # Configure Logger to see "Skipped" messages
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    return repo

def run_test():
    setup()
    
    # Repositories
    song_repo = SongRepository(DB_PATH)
    audit_repo = AuditRepository(DB_PATH)
    audit_service = AuditService(audit_repo)
    
    print("\n=== STEP 1: INSERT SONG ===")
    song = Song(
        name="Audit Test Song",
        source="C:/Music/audit_test.mp3",
        duration=180,
        bpm=120,
        is_active=True,
        performers=["Artist A"] # Non-empty list
    )
    # Composers, Lyricists etc are empty []
    
    song_id = song_repo.insert(song) # Should trigger Audit INSERT
    print(f"Inserted Song ID: {song_id}")
    
    print("\n=== STEP 2: UPDATE SONG ===")
    song.source_id = song_id
    song.bpm = 125
    song.name = "Audit Test Song (Remix)"
    song.composers = [] # Still empty
    # Update shouldn't log composers (Neither changed nor non-empty difference)
    
    success = song_repo.update(song) # Should trigger Audit UPDATE
    print(f"Update Success: {success}")
    
    print("\n=== STEP 3: DELETE SONG ===")
    success = song_repo.delete(song_id)
    print(f"Delete Success: {success}")
    
    print("\n=== STEP 4: VERIFY AUDIT LOG (Unified) ===")
    history = audit_service.get_unified_history(limit=50)
    
    if not history:
        print("X NO AUDIT LOGS FOUND!")
        return
        
    print(f"Found {len(history)} log entries:\n")
    print(f"{'TIME':<25} {'TYPE':<10} {'TABLE':<15} {'FIELD':<15} {'ID':<5} {'OLD':<20} {'NEW':<20}")
    print("-" * 110)
    
    for row in history:
        # Normalize keys for Row factory vs Dict
        r = dict(row)
        old_val = str(r['OldValue']) if r['OldValue'] is not None else "-"
        new_val = str(r['NewValue']) if r['NewValue'] is not None else "-"
        print(f"{r['Time']:<25} {r['EntryType']:<10} {r['TableName']:<15} {r['FieldName']:<15} {r['RecordID']:<5} {old_val:<20} {new_val:<20}")

    # Verify Counts
    # Expect:
    # Insert: ID, Path, Name, Duration, BPM, Active, Performers. (7 items). Excludes Composers [], etc.
    # Update: BPM, Name. (2 items). Excludes others.
    # Delete: ID, Path, Name, Duration... (7 items). Excludes Composers [], etc.
    
    print("\nSUMMARY:")
    inserts = [h for h in history if h['EntryType'] == 'CHANGE' and h['OldValue'] is None and h['NewValue'] is not None]
    updates = [h for h in history if h['EntryType'] == 'CHANGE' and h['OldValue'] is not None and h['NewValue'] is not None]
    deletes = [h for h in history if h['EntryType'] == 'CHANGE' and h['OldValue'] is not None and h['NewValue'] is None]

    print(f"Inserts: {len(inserts)} (Should exclude empty fields)")
    print(f"Updates: {len(updates)}")
    print(f"Deletes: {len(deletes)} (Should exclude empty fields)")
    
    # Check for empty strings
    empty_writes = [h for h in history if h['NewValue'] == "" or h['OldValue'] == ""]
    if empty_writes:
         print("X FOUND {len(empty_writes)} EMPTY WRITES! FILTER FAILED.")
         for e in empty_writes:
             print(f"  - {e['FieldName']}: '{e['OldValue']}' -> '{e['NewValue']}'")
    else:
         print("OK No Empty Writes detected.")

if __name__ == "__main__":
    run_test()
