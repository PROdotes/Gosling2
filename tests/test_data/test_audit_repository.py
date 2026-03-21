"""
Contract tests for AuditRepository.
Every assertion verifies EXACT values from the populated_db fixture.
"""

from src.data.audit_repository import AuditRepository


class TestGetActionsForTarget:
    """AuditRepository.get_actions_for_target contracts."""

    def test_rename_action_exists(self, populated_db):
        """ActionLog has: ActionID=1, RENAME on ArtistNames ID=33.

        All fields must be asserted since ActionLog INSERT omits
        timestamp, user_id, batch_id (they should be None).
        """
        repo = AuditRepository(populated_db)
        actions = repo.get_actions_for_target(33, "ArtistNames")

        assert len(actions) == 1, f"Expected 1 action, got {len(actions)}"
        action = actions[0]
        assert action.id == 1, f"Expected id=1, got {action.id}"
        assert (
            action.action_type == "RENAME"
        ), f"Expected 'RENAME', got {action.action_type}"
        assert (
            action.target_table == "ArtistNames"
        ), f"Expected 'ArtistNames', got {action.target_table}"
        assert action.target_id == "33", f"Expected '33', got {action.target_id}"
        assert (
            action.details == "User updated artist name"
        ), f"Expected 'User updated artist name', got {action.details}"
        assert (
            action.timestamp is not None
        ), "Expected auto-populated timestamp, got None"
        assert isinstance(
            action.timestamp, str
        ), f"Expected timestamp str, got {type(action.timestamp)}"
        assert action.user_id is None, f"Expected user_id=None, got {action.user_id}"
        assert action.batch_id is None, f"Expected batch_id=None, got {action.batch_id}"

    def test_no_actions_for_unknown_target(self, populated_db):
        """Target ID 999 has no entries in ActionLog."""
        repo = AuditRepository(populated_db)
        actions = repo.get_actions_for_target(999, "ArtistNames")
        assert (
            len(actions) == 0
        ), f"Expected 0 actions for unknown target, got {len(actions)}"

    def test_no_actions_for_wrong_table(self, populated_db):
        """ActionID=1 targets ArtistNames; querying Songs must return empty."""
        repo = AuditRepository(populated_db)
        actions = repo.get_actions_for_target(33, "Songs")
        assert (
            len(actions) == 0
        ), f"Expected 0 actions for wrong table, got {len(actions)}"

    def test_empty_db_returns_no_actions(self, empty_db):
        """Empty database has no action log entries."""
        repo = AuditRepository(empty_db)
        actions = repo.get_actions_for_target(1, "Songs")
        assert len(actions) == 0, f"Expected 0 actions in empty DB, got {len(actions)}"


class TestGetChangesForRecord:
    """AuditRepository.get_changes_for_record contracts."""

    def test_changelog_exists(self, populated_db):
        """ChangeLog: LogID=1, ArtistNames record 33, DisplayName: PinkPantheress -> Ines Prajo.

        All fields asserted; timestamp and batch_id are None (not in INSERT).
        """
        repo = AuditRepository(populated_db)
        changes = repo.get_changes_for_record(33, "ArtistNames")

        assert len(changes) == 1, f"Expected 1 change, got {len(changes)}"
        change = changes[0]
        assert change.id == 1, f"Expected id=1, got {change.id}"
        assert (
            change.table_name == "ArtistNames"
        ), f"Expected 'ArtistNames', got {change.table_name}"
        assert change.record_id == "33", f"Expected '33', got {change.record_id}"
        assert (
            change.field_name == "DisplayName"
        ), f"Expected 'DisplayName', got {change.field_name}"
        assert (
            change.old_value == "PinkPantheress"
        ), f"Expected 'PinkPantheress', got {change.old_value}"
        assert (
            change.new_value == "Ines Prajo"
        ), f"Expected 'Ines Prajo', got {change.new_value}"
        assert (
            change.timestamp is not None
        ), "Expected auto-populated timestamp, got None"
        assert isinstance(
            change.timestamp, str
        ), f"Expected timestamp str, got {type(change.timestamp)}"
        assert change.batch_id is None, f"Expected batch_id=None, got {change.batch_id}"

    def test_no_changes_for_unknown_record(self, populated_db):
        """Record 999 in Songs has no change log entries."""
        repo = AuditRepository(populated_db)
        changes = repo.get_changes_for_record(999, "Songs")
        assert (
            len(changes) == 0
        ), f"Expected 0 changes for unknown record, got {len(changes)}"

    def test_table_expansion_songs_returns_empty(self, populated_db):
        """Querying Songs also searches SongCredits, SongAlbums, etc.

        Fixture has no changes for any song-related table, so result is empty.
        """
        repo = AuditRepository(populated_db)
        changes = repo.get_changes_for_record(1, "Songs")
        assert (
            len(changes) == 0
        ), f"Expected 0 changes for song records, got {len(changes)}"

    def test_table_expansion_identities_finds_artist_names_change(self, populated_db):
        """Querying Identities also searches ArtistNames and GroupMemberships.

        Record 33 exists in ArtistNames ChangeLog, so it must be found.
        All fields of the returned AuditChange must be asserted.
        """
        repo = AuditRepository(populated_db)
        changes = repo.get_changes_for_record(33, "Identities")

        assert (
            len(changes) == 1
        ), f"Expected 1 change via table expansion, got {len(changes)}"
        change = changes[0]
        assert change.id == 1, f"Expected id=1, got {change.id}"
        assert (
            change.table_name == "ArtistNames"
        ), f"Expected 'ArtistNames', got {change.table_name}"
        assert change.record_id == "33", f"Expected '33', got {change.record_id}"
        assert (
            change.field_name == "DisplayName"
        ), f"Expected 'DisplayName', got {change.field_name}"
        assert (
            change.old_value == "PinkPantheress"
        ), f"Expected 'PinkPantheress', got {change.old_value}"
        assert (
            change.new_value == "Ines Prajo"
        ), f"Expected 'Ines Prajo', got {change.new_value}"
        assert (
            change.timestamp is not None
        ), "Expected auto-populated timestamp, got None"
        assert isinstance(
            change.timestamp, str
        ), f"Expected timestamp str, got {type(change.timestamp)}"
        assert change.batch_id is None, f"Expected batch_id=None, got {change.batch_id}"


class TestGetDeletedSnapshot:
    """AuditRepository.get_deleted_snapshot contracts."""

    def test_deleted_record_exists(self, populated_db):
        """DeletedRecords: DeleteID=1, Songs record 99, snapshot JSON.

        All fields asserted; deleted_at, restored_at, batch_id are None
        (not provided in INSERT).
        """
        repo = AuditRepository(populated_db)
        deleted = repo.get_deleted_snapshot(99, "Songs")

        assert deleted is not None, "Expected a DeletedRecord, got None"
        assert deleted.id == 1, f"Expected id=1, got {deleted.id}"
        assert (
            deleted.table_name == "Songs"
        ), f"Expected 'Songs', got {deleted.table_name}"
        assert deleted.record_id == "99", f"Expected '99', got {deleted.record_id}"
        assert (
            deleted.snapshot == '{"Title": "Deleted Song", "Type": "Song"}'
        ), f"Expected snapshot JSON, got {deleted.snapshot}"
        assert (
            deleted.deleted_at is not None
        ), "Expected auto-populated deleted_at, got None"
        assert isinstance(
            deleted.deleted_at, str
        ), f"Expected deleted_at str, got {type(deleted.deleted_at)}"
        assert (
            deleted.restored_at is None
        ), f"Expected restored_at=None, got {deleted.restored_at}"
        assert (
            deleted.batch_id is None
        ), f"Expected batch_id=None, got {deleted.batch_id}"

    def test_no_deleted_for_existing_record(self, populated_db):
        """Song 1 is NOT deleted; must return None."""
        repo = AuditRepository(populated_db)
        result = repo.get_deleted_snapshot(1, "Songs")
        assert result is None, f"Expected None for non-deleted record, got {result}"

    def test_wrong_table_returns_none(self, populated_db):
        """Record 99 is deleted from Songs, not Albums; must return None."""
        repo = AuditRepository(populated_db)
        result = repo.get_deleted_snapshot(99, "Albums")
        assert result is None, f"Expected None for wrong table, got {result}"

    def test_empty_db_returns_none(self, empty_db):
        """Empty database has no deleted records."""
        repo = AuditRepository(empty_db)
        result = repo.get_deleted_snapshot(1, "Songs")
        assert result is None, f"Expected None in empty DB, got {result}"


# ===================================================================
# Mapper Tests: _row_to_action
# ===================================================================
class TestRowToAction:
    def test_all_fields_present(self, mock_db_path):
        mock_row = {
            "ActionID": 1,
            "ActionLogType": "RENAME",
            "TargetTable": "ArtistNames",
            "ActionTargetID": 33,
            "ActionDetails": "User updated artist name",
            "ActionTimestamp": "2024-01-01T00:00:00",
            "UserID": "admin",
            "BatchID": "batch-1",
        }
        repo = AuditRepository(mock_db_path)
        result = repo._row_to_action(mock_row)
        assert result.id == 1
        assert result.action_type == "RENAME"
        assert result.target_table == "ArtistNames"
        assert result.target_id == "33"
        assert result.details == "User updated artist name"
        assert result.timestamp == "2024-01-01T00:00:00"
        assert result.user_id == "admin"
        assert result.batch_id == "batch-1"

    def test_null_fields(self, mock_db_path):
        mock_row = {
            "ActionID": None,
            "ActionLogType": "RENAME",
            "TargetTable": None,
            "ActionTargetID": None,
            "ActionDetails": None,
            "ActionTimestamp": None,
            "UserID": None,
            "BatchID": None,
        }
        repo = AuditRepository(mock_db_path)
        result = repo._row_to_action(mock_row)
        assert result.id is None
        assert result.action_type == "RENAME"
        assert result.target_table is None
        assert result.target_id is None
        assert result.details is None
        assert result.timestamp is None
        assert result.user_id is None
        assert result.batch_id is None


# ===================================================================
# Mapper Tests: _row_to_change
# ===================================================================
class TestRowToChange:
    def test_all_fields_present(self, mock_db_path):
        mock_row = {
            "LogID": 1,
            "LogTableName": "ArtistNames",
            "RecordID": 33,
            "LogFieldName": "DisplayName",
            "OldValue": "PinkPantheress",
            "NewValue": "Ines Prajo",
            "LogTimestamp": "2024-01-01T00:00:00",
            "BatchID": "batch-1",
        }
        repo = AuditRepository(mock_db_path)
        result = repo._row_to_change(mock_row)
        assert result.id == 1
        assert result.table_name == "ArtistNames"
        assert result.record_id == "33"
        assert result.field_name == "DisplayName"
        assert result.old_value == "PinkPantheress"
        assert result.new_value == "Ines Prajo"
        assert result.timestamp == "2024-01-01T00:00:00"
        assert result.batch_id == "batch-1"

    def test_null_fields(self, mock_db_path):
        mock_row = {
            "LogID": None,
            "LogTableName": "ArtistNames",
            "RecordID": 33,
            "LogFieldName": "DisplayName",
            "OldValue": None,
            "NewValue": None,
            "LogTimestamp": None,
            "BatchID": None,
        }
        repo = AuditRepository(mock_db_path)
        result = repo._row_to_change(mock_row)
        assert result.id is None
        assert result.table_name == "ArtistNames"
        assert result.record_id == "33"
        assert result.field_name == "DisplayName"
        assert result.old_value is None
        assert result.new_value is None
        assert result.timestamp is None
        assert result.batch_id is None


# ===================================================================
# Mapper Tests: _row_to_deleted
# ===================================================================
class TestRowToDeleted:
    def test_all_fields_present(self, mock_db_path):
        mock_row = {
            "DeleteID": 1,
            "DeletedFromTable": "Songs",
            "RecordID": 99,
            "FullSnapshot": '{"Title": "Deleted Song", "Type": "Song"}',
            "DeletedAt": "2024-01-01T00:00:00",
            "RestoredAt": None,
            "BatchID": "batch-1",
        }
        repo = AuditRepository(mock_db_path)
        result = repo._row_to_deleted(mock_row)
        assert result.id == 1
        assert result.table_name == "Songs"
        assert result.record_id == "99"
        assert result.snapshot == '{"Title": "Deleted Song", "Type": "Song"}'
        assert result.deleted_at == "2024-01-01T00:00:00"
        assert result.restored_at is None
        assert result.batch_id == "batch-1"

    def test_null_fields(self, mock_db_path):
        mock_row = {
            "DeleteID": None,
            "DeletedFromTable": "Songs",
            "RecordID": 99,
            "FullSnapshot": '{"Title": "Deleted Song"}',
            "DeletedAt": None,
            "RestoredAt": None,
            "BatchID": None,
        }
        repo = AuditRepository(mock_db_path)
        result = repo._row_to_deleted(mock_row)
        assert result.id is None
        assert result.table_name == "Songs"
        assert result.record_id == "99"
        assert result.deleted_at is None
        assert result.restored_at is None
        assert result.batch_id is None
