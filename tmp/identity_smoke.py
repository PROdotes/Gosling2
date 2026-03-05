import os
import sys
from pathlib import Path

# Add src to path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from v3core.data.artist_name_repository import ArtistNameRepository
from v3core.data.identity_repository import IdentityRepository

def identity_smoke_test():
    db_path = r'c:\Users\glazb\PycharmProjects\gosling2\sqldb\gosling2.db'
    if not os.path.exists(db_path):
        print("DB not found!")
        return

    name_repo = ArtistNameRepository(db_path)
    id_repo = IdentityRepository(db_path)
    
    # 1. Tier 1 Search
    search_term = "Ivan"
    print(f"--- Tier 1 Search for '{search_term}' ---")
    names = name_repo.find_by_string(search_term)
    for n in names:
        print(f"Found Alias: {n.display_name} (ID: {n.id}, Owner: {n.owner_identity_id})")
        
        # 2. Load the Identity
        identity = id_repo.get_by_id(n.owner_identity_id)
        if identity:
            print(f"  Identity: {identity.display_name} type={identity.identity_type}")
            
            # 3. Check Relationships
            relations = id_repo.get_memberships(identity.id)
            for rel in relations:
                side = "PARENT" if rel.parent_id == identity.id else "MEMBER"
                related_id = rel.child_id if side == "PARENT" else rel.parent_id
                print(f"    - {side} of ID: {related_id}")
        print("-" * 20)

if __name__ == "__main__":
    identity_smoke_test()
