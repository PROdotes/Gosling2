import os
import sys

# Ensure the project root is in the path so imports like `src.core.logger` work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.v3core.services.catalog_service import CatalogService
import sqlite3
import random

def main():
    db_path = "c:/Users/glazb/PycharmProjects/gosling2/sqldb/gosling2.db"
    if not os.path.exists(db_path):
        # Fallback to look around if sqldb/gosling2.db doesn't exist
        print(f"Checking {db_path}...")
        db_path = "c:/Users/glazb/PycharmProjects/gosling2/gosling3_stress_test.db"
        if not os.path.exists(db_path):
            print("DB not found.")
            return

    print(f"Using DB: {db_path}")

    # Find song by title "over me"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SourceID FROM MediaSources WHERE MediaName LIKE '%over me%' LIMIT 1")
        row = cursor.fetchone()
        
        if not row:
            print("Song 'over me' not found in the DB.")
            return
            
        random_song_id = row[0]
        
    print(f"Fetching Song ID: {random_song_id}")
    
    service = CatalogService(db_path)
    song = service.get_song(random_song_id)
    
    if song:
        print("\n--- SONG INFO ---")
        print(f"ID: {song.id}")
        print(f"Title: {song.title}")
        print(f"Duration (ms): {song.duration_ms}")
        print(f"BPM: {song.bpm}")
        print(f"Year: {song.year}")
        print(f"Path: {song.source_path}")
        print(f"Active: {song.is_active}")
        print("\n--- CREDITS ---")
        for credit in song.credits:
            print(f"- {credit.display_name} (Role ID: {credit.role_id})")
        print("-----------------")
    else:
        print("Failed to fetch song.")

if __name__ == "__main__":
    main()
