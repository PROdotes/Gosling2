
import os
import sqlite3
import sys
from types import SimpleNamespace

# Setup Project Path
project_root = r"c:\Users\glazb\PycharmProjects\gosling2"
sys.path.append(project_root)

# Mocking the Environment
from src.data.repositories.identity_repository import IdentityRepository
from src.data.repositories.artist_name_repository import ArtistNameRepository
from src.business.services.contributor_service import ContributorService

# Use a temp DB
DB_PATH = "test_merger.db"
if os.path.exists(DB_PATH): os.remove(DB_PATH)

def setup_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE Identities (
            IdentityID INTEGER PRIMARY KEY AUTOINCREMENT,
            IdentityType TEXT DEFAULT 'person',
            LegalName TEXT
        );
        CREATE TABLE ArtistNames (
            NameID INTEGER PRIMARY KEY AUTOINCREMENT,
            OwnerIdentityID INTEGER,
            DisplayName TEXT,
            SortName TEXT,
            IsPrimaryName INTEGER DEFAULT 1,
            FOREIGN KEY(OwnerIdentityID) REFERENCES Identities(IdentityID)
        );
        CREATE TABLE SongCredits (
            SourceID INTEGER,
            CreditedNameID INTEGER,
            RoleID INTEGER
        );
        CREATE TABLE AlbumCredits (
            AlbumID INTEGER,
            CreditedNameID INTEGER,
            RoleID INTEGER
        );
        CREATE TABLE GroupMemberships (
            MembershipID INTEGER PRIMARY KEY,
            GroupIdentityID INTEGER,
            MemberIdentityID INTEGER,
            CreditedAsNameID INTEGER
        );
        CREATE TABLE Roles (
            RoleID INTEGER PRIMARY KEY,
            RoleName TEXT
        );
        INSERT INTO Roles (RoleID, RoleName) VALUES (1, 'Artist');
    """)
    conn.commit()
    conn.close()

def run_repro():
    setup_db(DB_PATH)
    
    service = ContributorService(db_path=DB_PATH)
    
    # 1. Create Identity A (Freddie)
    print("Creating Artist A (Freddie)...")
    a = service.create("Freddie", "person")
    
    # 2. Create Identity B (Queen)
    print("Creating Artist B (Queen)...")
    b = service.create("Queen", "group")
    
    # 3. Merge A into B
    print(f"Merging {a.contributor_id} (Freddie) into {b.contributor_id} (Queen)...")
    service.merge(a.contributor_id, b.contributor_id)
    
    # 4. VERIFY DATABASE STATE
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check Identities count
    cursor.execute("SELECT COUNT(*) FROM Identities")
    id_count = cursor.fetchone()[0]
    print(f"Total Identities: {id_count} (Expected: 1)")
    
    # Check Primary Names for Queen's Identity
    # We need to find Queen's Identity first
    cursor.execute("SELECT OwnerIdentityID FROM ArtistNames WHERE NameID = ?", (b.contributor_id,))
    queen_identity_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT DisplayName, IsPrimaryName FROM ArtistNames WHERE OwnerIdentityID = ?", (queen_identity_id,))
    rows = cursor.fetchall()
    
    print("\nName Records for Remaining Identity:")
    primaries = 0
    for name, is_primary in rows:
        print(f" - {name}: IsPrimary={is_primary}")
        if is_primary == 1: primaries += 1
        
    conn.close()
    
    if primaries > 1:
        print("\n[REPRO FAILED] Found multiple primary names for one identity!")
        return False
    elif id_count > 1:
        print("\n[REPRO FAILED] Merge failed to delete source identity!")
        return False
    else:
        print("\n[SUCCESS] Merge logic is sound.")
        return True

if __name__ == "__main__":
    success = run_repro()
    if os.path.exists(DB_PATH): os.remove(DB_PATH)
    sys.exit(0 if success else 1)
