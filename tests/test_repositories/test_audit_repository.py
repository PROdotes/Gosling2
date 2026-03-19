"""
Contract tests for AuditRepository.
Every assertion verifies EXACT values from the populated_db fixture.
"""

from src.data.audit_repository import AuditRepository


class TestGetActionsForTarget:
    """AuditRepository.get_actions_for_target contracts."""

    def test_rename_action_exists(self, populated_db):
        """ActionLog has: ActionID=1, RENAME on ArtistNames ID=33."""
        repo = AuditRepository(populated_db)
        actions = repo.get_actions_for_target(33, "ArtistNames")

        assert len(actions) == 1
        action = actions[0]
        assert action.id == 1
        assert action.action_type == "RENAME"
        assert action.target_table == "ArtistNames"
        assert action.target_id == "33"
        assert action.details == "User updated artist name"

    def test_no_actions_for_unknown_target(self, populated_db):
        repo = AuditRepository(populated_db)
        actions = repo.get_actions_for_target(999, "ArtistNames")
        assert actions == []

    def test_no_actions_for_wrong_table(self, populated_db):
        """ActionID=1 targets ArtistNames, NOT Songs."""
        repo = AuditRepository(populated_db)
        actions = repo.get_actions_for_target(33, "Songs")
        assert actions == []

    def test_empty_db(self, empty_db):
        repo = AuditRepository(empty_db)
        assert repo.get_actions_for_target(1, "Songs") == []


class TestGetChangesForRecord:
    """AuditRepository.get_changes_for_record contracts."""

    def test_changelog_exists(self, populated_db):
        """ChangeLog: LogID=1, ArtistNames record 33, DisplayName: PinkPantheress -> Ines Prajo."""
        repo = AuditRepository(populated_db)
        changes = repo.get_changes_for_record(33, "ArtistNames")

        assert len(changes) == 1
        change = changes[0]
        assert change.id == 1
        assert change.table_name == "ArtistNames"
        assert change.record_id == "33"
        assert change.field_name == "DisplayName"
        assert change.old_value == "PinkPantheress"
        assert change.new_value == "Ines Prajo"

    def test_no_changes_for_unknown_record(self, populated_db):
        repo = AuditRepository(populated_db)
        changes = repo.get_changes_for_record(999, "Songs")
        assert changes == []

    def test_table_expansion_songs(self, populated_db):
        """When table='Songs', the query should also search SongCredits, SongAlbums, etc.
        With our data there are no changes for song records, so result should be empty.
        """
        repo = AuditRepository(populated_db)
        changes = repo.get_changes_for_record(1, "Songs")
        assert changes == []

    def test_table_expansion_identities(self, populated_db):
        """When table='Identities', query also searches ArtistNames and GroupMemberships.
        Record 33 is in ArtistNames ChangeLog - but record_id check is against the identity ID, not 33.
        So searching for identity 1 with table Identities should look in ArtistNames too.
        """
        repo = AuditRepository(populated_db)
        # The ChangeLog record has RecordID=33 and LogTableName='ArtistNames'
        # When we query get_changes_for_record(33, 'Identities'), it searches
        # Identities, ArtistNames, GroupMemberships for RecordID=33 or '33-%'
        changes = repo.get_changes_for_record(33, "Identities")
        # Should find the ArtistNames change since table expansion includes ArtistNames
        assert len(changes) == 1
        assert changes[0].field_name == "DisplayName"


class TestGetDeletedSnapshot:
    """AuditRepository.get_deleted_snapshot contracts."""

    def test_deleted_record_exists(self, populated_db):
        """DeletedRecords: DeleteID=1, Songs record 99, snapshot JSON."""
        repo = AuditRepository(populated_db)
        deleted = repo.get_deleted_snapshot(99, "Songs")

        assert deleted is not None
        assert deleted.id == 1
        assert deleted.table_name == "Songs"
        assert deleted.record_id == "99"
        assert deleted.snapshot == '{"Title": "Deleted Song", "Type": "Song"}'

    def test_no_deleted_for_existing_record(self, populated_db):
        """Song 1 is NOT deleted."""
        repo = AuditRepository(populated_db)
        assert repo.get_deleted_snapshot(1, "Songs") is None

    def test_wrong_table(self, populated_db):
        """Record 99 is deleted from Songs, NOT Albums."""
        repo = AuditRepository(populated_db)
        assert repo.get_deleted_snapshot(99, "Albums") is None

    def test_empty_db(self, empty_db):
        repo = AuditRepository(empty_db)
        assert repo.get_deleted_snapshot(1, "Songs") is None
