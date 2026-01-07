
import pytest
import sqlite3
import os
from pathlib import Path
from src.data.repositories.contributor_repository import ContributorRepository
from src.business.services.contributor_service import ContributorService
from src.data.repositories.audit_repository import AuditRepository
from src.data.models.contributor import Contributor

@pytest.fixture
def db_path(tmp_path):
    # BaseRepository closes connection, so we need a persistent file for the test duration
    path = tmp_path / "test_audit_saftey.db"
    return str(path)

@pytest.fixture
def service(db_path):
    # Initialize service with specific db_path
    service = ContributorService(db_path=db_path)
    # Ensure schema exists (BaseRepository does this on init, but good to be explicit)
    repo = ContributorRepository(db_path=db_path)
    repo._ensure_schema()
    return service

@pytest.fixture
def audit_repo(db_path):
    return AuditRepository(db_path=db_path)

def test_alias_linking_audit_trail(service, audit_repo):
    """Scenario: Artist Pink exists. Alias P!nk is added. Then deleted."""
    # 1. Create Artist
    pink = service.create(name="Pink", type="person")
    pink_id = pink.contributor_id
    
    # 2. Add Alias
    service.add_alias(pink_id, "P!nk")
    
    # 3. Verify Audit Insert (Table: ArtistNames)
    history = audit_repo.get_unified_log(limit=20)
    insert_logs = [h for h in history if h['TableName'] == 'ArtistNames' and h['EntryType'] == 'CHANGE']
    assert any(h['NewValue'] == "P!nk" for h in insert_logs)
    
    # 4. Delete Alias
    aliases = service.get_aliases(pink_id)
    alias_id = next(a.alias_id for a in aliases if a.alias_name == "P!nk")
    service.delete_alias(alias_id)
    
    # 5. Verify Audit Delete
    history = audit_repo.get_unified_log(limit=20)
    delete_logs = [h for h in history if h['TableName'] == 'ArtistNames' and h['EntryType'] == 'CHANGE' and h['NewValue'] is None]
    assert any(h['OldValue'] == "P!nk" for h in delete_logs)

def test_merge_relationship_cascade_audit(service, audit_repo):
    """Scenario: Freddie (in Queen) merges into Ella. Verify Queen link transfers and audits."""
    # 1. Setup Identities
    ella = service.create(name="Ella", type="person")
    ella_id = ella.contributor_id
    freddie = service.create(name="Freddie", type="person")
    freddie_id = freddie.contributor_id
    queen = service.create(name="Queen", type="group")
    queen_id = queen.contributor_id
    
    # Freddie is in Queen
    service.add_member(queen_id, freddie_id)
    
    # 2. Merge Freddie -> Ella
    service.merge(freddie_id, ella_id)
    
    # 3. Verify Data Shift
    history = audit_repo.get_unified_log(limit=50)
    
    # Check for GroupMemberships update
    group_shifts = [h for h in history if h['TableName'] == 'GroupMemberships' and h['EntryType'] == 'CHANGE']
    assert len(group_shifts) > 0
    
    # Identity ID merge: Freddie's identity is merged into Ella's
    # So GroupMemberships should show MemberIdentityID changing.
    # Note: service.merge actually re-parents names and transfers memberships.
    
    # We expect a MERGE action log
    merge_actions = [h for h in history if h['EntryType'] == 'MERGE']
    assert len(merge_actions) >= 1

def test_abdicate_audit(service, audit_repo):
    """Scenario: Swap primary and alias. Verify audit."""
    # 1. Setup
    pink = service.create(name="Pink", type="person")
    pink_id = pink.contributor_id
    service.add_alias(pink_id, "Alecia Moore")
    alias_id = service.get_aliases(pink_id)[0].alias_id
    
    # 2. Abdicate / Promote
    # ContributorService has abdicate_identity
    # We promote Alecia Moore to be the new primary for Pink's identity
    # And Pink becomes an alias for some other target (or just moved)
    # The test originally called promote_alias which was repo-level.
    # On Service it's abdicate_identity (old_id, heir_id, adopter_id)
    
    # Let's just create a target adopter
    adopter = service.create(name="Legacy Project", type="group")
    service.abdicate_identity(pink_id, alias_id, adopter.contributor_id)
    
    # 3. Verify Audit
    history = audit_repo.get_unified_log(limit=20)
    # Abdicate uses 'ABDICATE' action type usually in IdentityService
    abdicate_actions = [h for h in history if h['EntryType'] == 'ABDICATE']
    assert len(abdicate_actions) > 0

def test_batch_id_grouping(service, audit_repo):
    """Verify that a complex operation (Merge) uses a single BatchID for all logs."""
    # 1. Setup
    a = service.create(name="A", type="person")
    b = service.create(name="B", type="person")
    
    # 2. Merge
    service.merge(a.contributor_id, b.contributor_id)
    
    # 3. Fetch History
    history = audit_repo.get_unified_log(limit=50)
    
    # Find the MERGE action
    merge_action = next(h for h in history if h['EntryType'] == 'MERGE')
    batch_id = merge_action['BatchID']
    assert batch_id is not None
    
    # Find the Change logs for the same operation
    related_changes = [h for h in history if h['BatchID'] == batch_id and h['EntryType'] == 'CHANGE']
    
    # In a merge, we expect re-parenting of names in ArtistNames
    assert any(h['TableName'] == 'ArtistNames' for h in related_changes)
    print(f"Verified Batch Grouping: {len(related_changes)} changes linked to MERGE via {batch_id}")
