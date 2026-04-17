"""
Contract tests for AuditService.
Tests the unified timeline merge of ActionLog + ChangeLog + DeletedRecords.
Every assertion verifies EXACT values from the populated_db fixture.
"""

from src.services.audit_service import AuditService


class TestGetHistoryWithData:
    """AuditService.get_history contracts for records WITH audit data."""

    def test_artist_name_rename_timeline(self, audit_service):
        """ArtistNames ID=33: has 1 ACTION (RENAME) + 1 CHANGE (DisplayName). Timeline should contain exactly 2 entries."""
        history = audit_service.get_history(33, "ArtistNames")

        assert isinstance(history, list), f"Expected list, got {type(history)}"
        assert len(history) == 2, f"Expected 2 timeline entries, got {len(history)}"

        # Verify the ACTION entry
        action = next(h for h in history if h["type"] == "ACTION")
        assert action["timestamp"] is not None, (
            f"Expected timestamp not None, got {action['timestamp']}"
        )
        assert action["type"] == "ACTION", (
            f"Expected type='ACTION', got '{action['type']}'"
        )
        assert action["label"] == "RENAME", (
            f"Expected label='RENAME', got '{action['label']}'"
        )
        assert action["details"] == "User updated artist name", (
            f"Expected details='User updated artist name', got '{action['details']}'"
        )
        assert action["user"] is None, f"Expected user=None, got {action['user']}"
        assert action["batch"] is None, f"Expected batch=None, got {action['batch']}"

        # Verify the CHANGE entry
        change = next(h for h in history if h["type"] == "CHANGE")
        assert change["timestamp"] is not None, (
            f"Expected timestamp not None, got {change['timestamp']}"
        )
        assert change["type"] == "CHANGE", (
            f"Expected type='CHANGE', got '{change['type']}'"
        )
        assert change["label"] == "Updated DisplayName", (
            f"Expected label='Updated DisplayName', got '{change['label']}'"
        )
        assert change["old"] == "PinkPantheress", (
            f"Expected old='PinkPantheress', got '{change['old']}'"
        )
        assert change["new"] == "Ines Prajo", (
            f"Expected new='Ines Prajo', got '{change['new']}'"
        )
        assert change["batch"] is None, f"Expected batch=None, got {change['batch']}"

    def test_deleted_record_timeline(self, audit_service):
        """Songs ID=99: only a DeletedRecord exists. Should have 1 LIFECYCLE entry."""
        history = audit_service.get_history(99, "Songs")

        assert isinstance(history, list), f"Expected list, got {type(history)}"
        assert len(history) == 1, f"Expected 1 timeline entry, got {len(history)}"

        entry = history[0]
        assert entry["timestamp"] is not None, (
            f"Expected timestamp not None, got {entry['timestamp']}"
        )
        assert entry["type"] == "LIFECYCLE", (
            f"Expected type='LIFECYCLE', got '{entry['type']}'"
        )
        assert entry["label"] == "RECORD DELETED", (
            f"Expected label='RECORD DELETED', got '{entry['label']}'"
        )
        assert entry["snapshot"] == '{"Title": "Deleted Song", "Type": "Song"}', (
            f"Expected snapshot with deleted song JSON, got '{entry['snapshot']}'"
        )
        assert entry["batch"] is None, f"Expected batch=None, got {entry['batch']}"

    def test_timeline_is_sorted_descending(self, audit_service):
        """Timeline entries must be sorted by timestamp descending (newest first)."""
        history = audit_service.get_history(33, "ArtistNames")

        assert len(history) >= 1, f"Expected at least 1 entry, got {len(history)}"
        timestamps = [h["timestamp"] for h in history]
        assert timestamps == sorted(timestamps, reverse=True), (
            f"Expected descending timestamps, got {timestamps}"
        )


class TestGetHistoryEmpty:
    """AuditService.get_history contracts for records with NO audit data."""

    def test_no_history_for_existing_song(self, audit_service):
        """Song 1 exists but has no ActionLog/ChangeLog/DeletedRecords entries."""
        history = audit_service.get_history(1, "Songs")

        assert isinstance(history, list), f"Expected list, got {type(history)}"
        assert history == [], f"Expected empty list, got {history}"

    def test_no_history_for_nonexistent_record(self, audit_service):
        """Nonexistent record should return empty timeline, not an error."""
        history = audit_service.get_history(99999, "Songs")

        assert isinstance(history, list), f"Expected list, got {type(history)}"
        assert history == [], f"Expected empty list, got {history}"

    def test_wrong_table_returns_empty(self, audit_service):
        """ArtistNames ID=33 has data, but querying 'Publishers' table should return nothing."""
        history = audit_service.get_history(33, "Publishers")

        assert isinstance(history, list), f"Expected list, got {type(history)}"
        assert history == [], f"Expected empty list, got {history}"

    def test_empty_db(self, audit_service_empty):
        """Empty DB should return empty timeline for any query."""
        history = audit_service_empty.get_history(1, "Songs")

        assert isinstance(history, list), f"Expected list, got {type(history)}"
        assert history == [], f"Expected empty list, got {history}"


class TestGetHistoryChangeLabeling:
    """Verify change labels include related table context."""

    def test_same_table_change_no_prefix(self, audit_service):
        """When change.table_name == query table, label is 'Updated {field}' without prefix."""
        history = audit_service.get_history(33, "ArtistNames")

        assert len(history) == 2, f"Expected 2 entries, got {len(history)}"
        change = next(h for h in history if h["type"] == "CHANGE")
        assert change["label"] == "Updated DisplayName", (
            f"Expected label='Updated DisplayName', got '{change['label']}'"
        )

    def test_cross_table_change_gets_prefix(self, populated_db):
        """When change is from a related table, label should be '[RelatedTable] Updated {field}'."""
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

        assert isinstance(history, list), f"Expected list, got {type(history)}"
        assert len(history) == 1, (
            f"Expected 1 cross-table change entry, got {len(history)}"
        )
        change = history[0]
        assert change["type"] == "CHANGE", (
            f"Expected type='CHANGE', got '{change['type']}'"
        )
        assert change["label"] == "[SongCredits] Updated CreditedNameID", (
            f"Expected label='[SongCredits] Updated CreditedNameID', got '{change['label']}'"
        )


class TestGetHistoryTimelineStructure:
    """Verify the exact structure of timeline dictionaries."""

    def test_action_entry_keys(self, audit_service):
        """ACTION entries must have exactly: timestamp, type, label, details, user, batch."""
        history = audit_service.get_history(33, "ArtistNames")
        action = next(h for h in history if h["type"] == "ACTION")
        assert set(action.keys()) == {
            "timestamp",
            "type",
            "label",
            "details",
            "user",
            "batch",
        }, (
            f"Expected keys {{timestamp,type,label,details,user,batch}}, got {set(action.keys())}"
        )

    def test_change_entry_keys(self, audit_service):
        """CHANGE entries must have exactly: timestamp, type, label, old, new, batch."""
        history = audit_service.get_history(33, "ArtistNames")
        change = next(h for h in history if h["type"] == "CHANGE")
        assert set(change.keys()) == {
            "timestamp",
            "type",
            "label",
            "old",
            "new",
            "batch",
        }, (
            f"Expected keys {{timestamp,type,label,old,new,batch}}, got {set(change.keys())}"
        )

    def test_lifecycle_entry_keys(self, audit_service):
        """LIFECYCLE entries must have exactly: timestamp, type, label, snapshot, batch."""
        history = audit_service.get_history(99, "Songs")
        assert len(history) == 1, f"Expected 1 entry, got {len(history)}"
        lifecycle = history[0]
        assert set(lifecycle.keys()) == {
            "timestamp",
            "type",
            "label",
            "snapshot",
            "batch",
        }, (
            f"Expected keys {{timestamp,type,label,snapshot,batch}}, got {set(lifecycle.keys())}"
        )
