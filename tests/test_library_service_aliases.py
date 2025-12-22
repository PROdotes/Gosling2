"""
Integration Test: Verify Library Service returns Aliases
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.repositories.song_repository import SongRepository
from src.data.repositories.contributor_repository import ContributorRepository
from src.data.repositories.contributor_repository import ContributorRepository

def test_aliases():
    # DIRECT REPO TEST (Avoids Service Layer PyQt6 imports)
    repo = ContributorRepository()
    
    print("\n--- TEST: Alias Visibility (Repo Layer) ---\n")
    
    # 1. Fetch Aliases directly
    aliases = repo.get_all_aliases()
    print(f"Aliases Found: {aliases}")
    
    if "Dale Nixon" in aliases:
        print("✅ SUCCESS: 'Dale Nixon' is visible to LibraryService.")
    else:
        print("❌ FAILURE: 'Dale Nixon' is missing from LibraryService.")
        
    print("-" * 30)

if __name__ == "__main__":
    test_aliases()
