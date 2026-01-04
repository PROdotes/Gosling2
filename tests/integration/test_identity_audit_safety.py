
import pytest
import sqlite3
import os
from pathlib import Path
from src.data.repositories.contributor_repository import ContributorRepository
from src.data.repositories.audit_repository import AuditRepository
from src.data.models.contributor import Contributor

@pytest.fixture
def db_path(tmp_path):
    # BaseRepository closes connection, so we need a persistent file for the test duration
    path = tmp_path / "test_audit.db"
    return str(path)

@pytest.fixture
def repo(db_path):
    repo = ContributorRepository(db_path=db_path)
    repo._ensure_schema()
    return repo

@pytest.fixture
def audit_repo(db_path):
    return AuditRepository(db_path=db_path)

def test_alias_linking_audit_trail(repo, audit_repo):
    """Scenario: Artist Pink exists. Alias P!nk is added. Then unlinked."""
    # 1. Create Artist
    pink = repo.create(name="Pink", type="person")
    pink_id = pink.contributor_id
    
    # 2. Add Alias
    repo.add_alias(pink_id, "P!nk")
    
    # 3. Verify Audit Insert
    history = audit_repo.get_unified_log(limit=10)
    insert_logs = [h for h in history if h['TableName'] == 'ContributorAliases' and h['EntryType'] == 'CHANGE']
    assert any(h['NewValue'] == "P!nk" for h in insert_logs)
    
    # 4. Delete Alias
    alias_id = repo.get_aliases(pink_id)[0][0]
    repo.delete_alias(alias_id)
    
    # 5. Verify Audit Delete
    history = audit_repo.get_unified_log(limit=10)
    delete_logs = [h for h in history if h['TableName'] == 'ContributorAliases' and h['EntryType'] == 'CHANGE' and h['NewValue'] is None]
    assert any(h['OldValue'] == "P!nk" for h in delete_logs)

def test_merge_relationship_cascade_audit(repo, audit_repo):
    """Scenario: Freddie (in Queen) merges into Ella. Verify Queen link transfers and audits."""
    # 1. Setup Identities
    ella = repo.create(name="Ella", type="person")
    ella_id = ella.contributor_id
    freddie = repo.create(name="Freddie", type="person")
    freddie_id = freddie.contributor_id
    queen = repo.create(name="Queen", type="group")
    queen_id = queen.contributor_id
    
    # Freddie is in Queen
    repo.add_member(queen_id, freddie_id)
    
    # 2. Merge Freddie -> Ella
    repo.merge(freddie_id, ella_id)
    
    # 3. Verify Data Shift
    history = audit_repo.get_unified_log(limit=50)
    
    # Check for GroupMembers update
    group_shifts = [h for h in history if h['TableName'] == 'GroupMembers' and h['EntryType'] == 'CHANGE']
    assert len(group_shifts) > 0
    # One entry should show Freddie's old ID moving to Ella's ID
    found_shift = False
    for h in group_shifts:
        # Note: log values might be strings
        if str(h['OldValue']) == str(freddie_id) and str(h['NewValue']) == str(ella_id):
            found_shift = True
            break
    assert found_shift, "Group membership shift was not audited"
    
    # 4. Check for Action Log
    merge_actions = [h for h in history if h['EntryType'] == 'MERGE']
    assert len(merge_actions) >= 1

def test_promotion_audit(repo, audit_repo):
    """Scenario: Swap primary and alias. Verify audit."""
    # 1. Setup
    pink = repo.create(name="Pink", type="person")
    pink_id = pink.contributor_id
    alias_id = repo.add_alias(pink_id, "Alecia Moore")
    
    # 2. Promote
    repo.promote_alias(pink_id, alias_id)
    
    # 3. Verify Audit
    history = audit_repo.get_unified_log(limit=20)
    promotions = [h for h in history if h['EntryType'] == 'PROMOTE_ALIAS']
    assert len(promotions) > 0
    assert "Alecia Moore" in str(promotions[0]['NewValue'])

def test_batch_id_grouping(repo, audit_repo):
    """Verify that a complex operation (Merge) uses a single BatchID for all logs."""
    # 1. Setup
    a = repo.create(name="A", type="person")
    b = repo.create(name="B", type="person")
    
    # 2. Merge
    repo.merge(a.contributor_id, b.contributor_id)
    
    # 3. Fetch History
    history = audit_repo.get_unified_log(limit=20)
    
    # Find the MERGE action
    merge_action = next(h for h in history if h['EntryType'] == 'MERGE')
    batch_id = merge_action['BatchID']
    assert batch_id is not None
    
    # Find the Change logs for the same timestamp/operation
    related_changes = [h for h in history if h['BatchID'] == batch_id and h['EntryType'] == 'CHANGE']
    
    # In a merge, we expect at least the deletion of the source and maybe alias creation
    assert len(related_changes) > 0
    print(f"Verified Batch Grouping: {len(related_changes)} changes linked to MERGE via {batch_id}")
