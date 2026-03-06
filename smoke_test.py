import os
from src.services.catalog_service import CatalogService

def smoke_test():
    db_path = os.path.join("sqldb", "gosling2.db")
    if not os.path.exists(db_path):
        print(f"FAILED: Database not found at {db_path}")
        return

    service = CatalogService(db_path)
    
    # Try to get song ID 1 (standard starting ID)
    try:
        song = service.get_song(1)
        if song:
            print("\n" + "="*40)
            print(f"SUCCESS: Retrieved song: {song.title}")
            print(f"ID:      {song.id}")
            print(f"Path:    {song.source_path}")
            print(f"BPM:     {song.bpm}")
            print(f"Year:    {song.year}")
            print(f"Credits: {len(song.credits)}")
            for credit in song.credits:
                print(f"  - [{credit.role_id}] {credit.display_name}")
            print("="*40 + "\n")
        else:
            print("FAILED: get_song(1) returned None (Database might be empty or ID 1 missing)")
    except Exception as e:
        print(f"CRASHED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    smoke_test()
