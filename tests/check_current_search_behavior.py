"""
System Interaction Test: Current Search Behavior (Groups/Unified Artist)
Mimics the application's search call to verify the broken state.
"""
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.repositories.song_repository import SongRepository

def test_search():
    repo = SongRepository()
    
    print("\n--- TEST: Current Search Behavior ---\n")

    scenarios = [
        ("Nirvana", ["Lithium"]),           # Expect Success (Direct Match)
        ("Dave Grohl", ["Lithium", "Pretender"]), # Expect Failure (Member Traversal missing)
        ("Dale Nixon", ["Lithium", "Pretender"]), # Expect Failure (Alias -> Member missing)
    ]

    for query_name, expected_songs in scenarios:
        print(f"Query: '{query_name}'")
        try:
            # Mimic the Unified Artist call
            headers, rows = repo.get_by_unified_artists([query_name])
            
            # Rows are tuples, index 1 is Name
            found_titles = [r[1] for r in rows] if rows else []
            
            print(f"   Found: {found_titles}")
            
            # Simple verification
            success = any(t in found_titles for t in expected_songs)
            if success:
                print(f"   SUCCESS (Matched expected)")
            else:
                print(f"   FAILURE (Missing expected connections)")
                
        except Exception as e:
            print(f"   CRASH: {e}")
        
        print("-" * 30)

if __name__ == "__main__":
    test_search()
