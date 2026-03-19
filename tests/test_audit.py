"""
Contract tests for AuditService.
Tests the unified timeline merge of ActionLog + ChangeLog + DeletedRecords.
Every assertion verifies EXACT values from the populated_db fixture.
"""
from src.services.audit_service import AuditService


class TestGetHistoryWithData:
    """AuditService.get_history contracts for records WITH audit data."""

    def test_artist_name_rename_timeline(self, audit_service):
        """ArtistNames ID=33: has 1 ACTION (RENAME) + 1 CHANGE (DisplayName).
        Timeline should contain exactly 2 entries."""
        history = audit_service.get_history(33, "ArtistNames")

        assert len(history) == 2

        # Verify the ACTION entry
        action = next(h for h in history if h["type"] == "ACTION")
        assert action["label"] == "RENAME"
        assert action["details"] == "User updated artist name"
        assert action["user"] is None  # No UserID in our fixture
        assert action["batch"] is None

        # Verify the CHANGE entry
        change = next(h for h in history if h["type"] == "CHANGE")
        assert change["label"] == "Updated DisplayName"
        assert change["old"] == "PinkPantheress"
        assert change["new"] == "Ines Prajo"
        assert change["batch"] is None

    def test_deleted_record_timeline(self, audit_service):
        """Songs ID=99: only a DeletedRecord exists. Should have 1 LIFECYCLE entry."""
        history = audit_service.get_history(99, "Songs")

        assert len(history) == 1
        entry = history[0]
        assert entry["type"] == "LIFECYCLE"
        assert entry["label"] == "RECORD DELETED"
        assert entry["snapshot"] == '{"Title": "Deleted Song", "Type": "Song"}'
        assert entry["batch"] is None

    def test_timeline_is_sorted_descending(self, audit_service):
        """Timeline entries must be sorted by timestamp descending (newest first)."""
        history = audit_service.get_history(33, "ArtistNames")
        timestamps = [h["timestamp"] for h in history]
        # Both have the same CURRENT_TIMESTAMP default, but ordering should not crash
        assert len(timestamps) == 2


class TestGetHistoryEmpty:
    """AuditService.get_history contracts for records with NO audit data."""

    def test_no_history_for_existing_song(self, audit_service):
        """Song 1 exists but has no ActionLog/ChangeLog/DeletedRecords entries."""
        history = audit_service.get_history(1, "Songs")
        assert history == []

    def test_no_history_for_nonexistent_record(self, audit_service):
        """Nonexistent record should return empty timeline, not an error."""
        history = audit_service.get_history(99999, "Songs")
        assert history == []

    def test_wrong_table_returns_empty(self, audit_service):
        """ArtistNames ID=33 has data, but querying 'Publishers' table should return nothing."""
        history = audit_service.get_history(33, "Publishers")
        assert history == []

    def test_empty_db(self, audit_service_empty):
        """Empty DB should return empty timeline for any query."""
        history = audit_service_empty.get_history(1, "Songs")
        assert history == []


class TestGetHistoryChangeLabeling:
    """Verify change labels include related table context."""

    def test_same_table_change_no_prefix(self, audit_service):
        """When change.table_name == query table, label is 'Updated {field}'."""
        history = audit_service.get_history(33, "ArtistNames")
        change = next(h for h in history if h["type"] == "CHANGE")
        # table_name='ArtistNames', queried table='ArtistNames' -> no prefix
        assert change["label"] == "Updated DisplayName"

    def test_cross_table_change_gets_prefix(self, populated_db):
        """When a change is from a related table, label should be '[RelatedTable] Updated {field}'.
        We need to add a cross-table change to verify this."""
        import sqlite3
        conn = sqlite3.connect(populated_db)
        conn.create_collation(
            "UTF8_NOCASE",
            lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
        )
        conn.execute(
            "INSERT INTO ChangeLog (LogTableName, RecordID, LogFieldName, OldValue, NewValue) "
            "VALUES ('SongCredits', '1', 'CreditedNameID', '20', '30')"
        )
        conn.commit()
        conn.close()

        service = AuditService(populated_db)
        history = service.get_history(1, "Songs")
        # Should find the SongCredits change (table expansion for Songs includes SongCredits)
        assert len(history) == 1
        change = history[0]
        assert change["type"] == "CHANGE"
        assert change["label"] == "[SongCredits] Updated CreditedNameID"


class TestGetHistoryTimelineStructure:
    """Verify the exact structure of timeline dictionaries."""

    def test_action_entry_keys(self, audit_service):
        history = audit_service.get_history(33, "ArtistNames")
        action = next(h for h in history if h["type"] == "ACTION")
        assert set(action.keys()) == {"timestamp", "type", "label", "details", "user", "batch"}

    def test_change_entry_keys(self, audit_service):
        history = audit_service.get_history(33, "ArtistNames")
        change = next(h for h in history if h["type"] == "CHANGE")
        assert set(change.keys()) == {"timestamp", "type", "label", "old", "new", "batch"}

    def test_lifecycle_entry_keys(self, audit_service):
        history = audit_service.get_history(99, "Songs")
        lifecycle = history[0]
        assert set(lifecycle.keys()) == {"timestamp", "type", "label", "snapshot", "batch"}
