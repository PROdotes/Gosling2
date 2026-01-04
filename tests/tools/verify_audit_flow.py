
import os
import sys
import sqlite3
import json

# Setup path
sys.path.append(os.getcwd())

from src.business.services.library_service import LibraryService
from src.business.services.song_service import SongService
from src.business.services.contributor_service import ContributorService
from src.business.services.album_service import AlbumService
from src.business.services.publisher_service import PublisherService
from src.business.services.tag_service import TagService

def verify():
    print("--- Audit Flow Verification ---")
    
    # 1. Initialize Services
    lib = LibraryService(
        SongService(), 
        ContributorService(), 
        AlbumService(), 
        PublisherService(), 
        TagService()
    )
    contrib_service = lib.contributor_service
    
    # 2. Setup Identities
    print("Creating identities...")
    ella, _ = contrib_service.get_or_create("Ella Maren", "person")
    freddie, _ = contrib_service.get_or_create("Freddie Mercury", "person")
    
    ella_id = ella.contributor_id
    freddie_id = freddie.contributor_id
    print(f"Ella: {ella_id}, Freddie: {freddie_id}")
    
    # 3. Perform Merge
    print(f"Merging {freddie_id} into {ella_id}...")
    contrib_service.merge(freddie_id, ella_id)
    
    # 4. Check Database
    conn = sqlite3.connect('sqldb/gosling2.sqlite3')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n[ACTION LOG]")
    cursor.execute("SELECT * FROM ActionLog ORDER BY ActionID DESC LIMIT 5")
    actions = cursor.fetchall()
    for a in actions:
        print(dict(a))
        
    print("\n[CHANGE LOG]")
    cursor.execute("SELECT * FROM ChangeLog WHERE LogTableName IN ('Contributors', 'ContributorAliases') ORDER BY LogID DESC LIMIT 10")
    changes = cursor.fetchall()
    for c in changes:
        print(dict(c))
        
    conn.close()

if __name__ == "__main__":
    verify()
