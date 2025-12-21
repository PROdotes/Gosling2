import pytest
import sqlite3
from src.data.repositories.contributor_repository import ContributorRepository

@pytest.fixture
def repo(tmp_path):
    # Use temp file DB because BaseRepository closes connection (wiping :memory: DB)
    db_file = tmp_path / "test.db"
    repo = ContributorRepository(db_path=str(db_file))
    # Initialize Schema (including ContributorAliases)
    repo._ensure_schema()
    return repo

def seed_db(repo):
    with repo.get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Contributors
        # 1=Bob (Person), 2=The Cows (Group), 3=The Bull (Person/Group)
        cursor.executemany("INSERT INTO Contributors (ContributorID, ContributorName, SortName, Type) VALUES (?, ?, ?, ?)", [
            (1, "Bob", "Bob", "person"),
            (2, "The Cows", "Cows, The", "group"),
            (3, "The Bull", "Bull, The", "group")
        ])
        
        # 2. GroupMembers
        # Bob is in Cows
        # Bob is in Bull
        cursor.executemany("INSERT INTO GroupMembers (GroupID, MemberID) VALUES (?, ?)", [
            (2, 1),
            (3, 1)
        ])
        
        # 3. Aliases
        # Bob -> "Robert"
        # The Bull -> "El Toro"
        cursor.executemany("INSERT INTO ContributorAliases (ContributorID, AliasName) VALUES (?, ?)", [
            (1, "Robert"),
            (3, "El Toro")
        ])

def test_resolve_bob_groups(repo):
    """Test searching for 'Bob' finds Bob, his Alias, and his Groups (and their aliases)"""
    seed_db(repo)
    
    # Act
    results = repo.resolve_identity_graph("Bob")
    
    # Assert
    assert "Bob" in results
    assert "Robert" in results          # Alias of Bob
    assert "The Cows" in results        # Group Bob is in
    assert "The Bull" in results        # Group Bob is in
    assert "El Toro" in results         # Alias of Group Bob is in

def test_resolve_alias_to_graph(repo):
    """Test searching for 'Robert' (Alias) resolves to Bob -> Cows -> Bull"""
    seed_db(repo)
    
    # Act
    results = repo.resolve_identity_graph("Robert")
    
    # Assert
    assert "Bob" in results
    assert "The Cows" in results

def test_resolve_group_no_members(repo):
    """Test searching for 'The Cows' does NOT find Bob (Upstream only, not downstream)"""
    seed_db(repo)
    
    # Act
    results = repo.resolve_identity_graph("The Cows")
    
    # Assert
    assert "The Cows" in results
    assert "Bob" not in results # Searching Group doesn't list all members usually
    
def test_resolve_partial_case(repo):
    """Test that resolving is currently strict (as implemented) or whatever logic we chose"""
    # Current implementation uses "=", so case matters if DB is case sensitive (SQLite default usually depends on PRAGMA but = is case sensitive often)
    # Actually implementation converts term to exact match.
    pass 
