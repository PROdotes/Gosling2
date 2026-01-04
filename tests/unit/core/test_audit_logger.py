"""
Logic tests for AuditLogger (Level 1: Happy Path & Polite Failures).
Per TESTING.md: Tests for diff calculation and audit log dispatching.
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from src.core.audit_logger import AuditLogger


class TestAuditLogger:
    """Unit tests for AuditLogger diff calculation and logging operations."""
    
    @pytest.fixture
    def mock_connection(self):
        """Fixture providing a mock database connection."""
        return MagicMock()
    
    @pytest.fixture
    def logger(self, mock_connection):
        """Fixture providing AuditLogger instance with mocked repository."""
        # Patch at the import location
        with patch('src.data.repositories.audit_repository.AuditRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            audit_logger = AuditLogger(mock_connection)
            audit_logger.audit_repo = mock_repo  # Ensure we have the mock
            
            yield audit_logger, mock_repo
    
    class TestLogInsert:
        """Tests for log_insert method."""
        
        def test_log_insert_creates_change_logs(self, logger):
            """Test that insert logging creates change log entries for all fields."""
            audit_logger, mock_repo = logger
            
            new_data = {
                "title": "New Song",
                "artist": "Test Artist",
                "bpm": 120
            }
            
            audit_logger.log_insert("Songs", 42, new_data)
            
            # Verify audit_repo.insert_change_logs was called
            assert mock_repo.insert_change_logs.called
            
            # Get the rows that were logged
            call_args = mock_repo.insert_change_logs.call_args[0][0]
            
            # Should have 3 rows (one per field)
            assert len(call_args) == 3
            
            # Verify structure: (table, id, field, old, new, batch_id)
            for row in call_args:
                assert row[0] == "Songs"  # table_name
                assert row[1] == 42  # record_id
                assert row[3] is None  # old_value (always None for insert)
                assert row[4] is not None  # new_value
                assert row[5] is not None  # batch_id
        
        def test_log_insert_skips_none_values(self, logger):
            """Test that None values are not logged."""
            audit_logger, mock_repo = logger
            
            new_data = {
                "title": "Song",
                "artist": None,  # Should be skipped
                "bpm": 120
            }
            
            audit_logger.log_insert("Songs", 1, new_data)
            
            call_args = mock_repo.insert_change_logs.call_args[0][0]
            
            # Should only have 2 rows (artist skipped)
            assert len(call_args) == 2
            
            # Verify artist is not in logged fields
            logged_fields = [row[2] for row in call_args]
            assert "artist" not in logged_fields
        
        def test_log_insert_handles_empty_data(self, logger):
            """Test that empty data dict doesn't cause errors."""
            audit_logger, mock_repo = logger
            
            audit_logger.log_insert("Songs", 1, {})
            
            # Should not call repository
            assert not mock_repo.insert_change_logs.called
        
        def test_log_insert_normalizes_lists(self, logger):
            """Test that list values are normalized to comma-separated strings."""
            audit_logger, mock_repo = logger
            
            new_data = {
                "genres": ["Rock", "Alternative", "Indie"]
            }
            
            audit_logger.log_insert("Songs", 1, new_data)
            
            call_args = mock_repo.insert_change_logs.call_args[0][0]
            
            # Should have 1 row
            assert len(call_args) == 1
            
            # Verify list was normalized (sorted and joined)
            assert call_args[0][4] == "Alternative, Indie, Rock"
    
    class TestLogUpdate:
        """Tests for log_update method."""
        
        def test_log_update_detects_changes(self, logger):
            """Test that update logging only logs changed fields."""
            audit_logger, mock_repo = logger
            
            old_data = {
                "title": "Old Title",
                "artist": "Same Artist",
                "bpm": 120
            }
            
            new_data = {
                "title": "New Title",  # Changed
                "artist": "Same Artist",  # Unchanged
                "bpm": 140  # Changed
            }
            
            audit_logger.log_update("Songs", 42, old_data, new_data)
            
            call_args = mock_repo.insert_change_logs.call_args[0][0]
            
            # Should only log 2 changes (title and bpm)
            assert len(call_args) == 2
            
            # Verify changed fields
            logged_fields = {row[2] for row in call_args}
            assert "title" in logged_fields
            assert "bpm" in logged_fields
            assert "artist" not in logged_fields
        
        def test_log_update_skips_if_no_changes(self, logger):
            """Test that no logs are created if data is identical."""
            audit_logger, mock_repo = logger
            
            data = {
                "title": "Same Title",
                "artist": "Same Artist"
            }
            
            audit_logger.log_update("Songs", 1, data, data)
            
            # Should not call repository
            assert not mock_repo.insert_change_logs.called
        
        def test_log_update_handles_empty_data(self, logger):
            """Test that empty data dicts don't cause errors."""
            audit_logger, mock_repo = logger
            
            audit_logger.log_update("Songs", 1, {}, {})
            
            # Should not call repository
            assert not mock_repo.insert_change_logs.called
        
        def test_log_update_detects_list_changes(self, logger):
            """Test that changes in list fields are detected."""
            audit_logger, mock_repo = logger
            
            old_data = {"genres": ["Rock", "Pop"]}
            new_data = {"genres": ["Rock", "Jazz"]}
            
            audit_logger.log_update("Songs", 1, old_data, new_data)
            
            call_args = mock_repo.insert_change_logs.call_args[0][0]
            
            # Should detect change
            assert len(call_args) == 1
            assert call_args[0][2] == "genres"
            assert call_args[0][3] == "Pop, Rock"  # Old (sorted)
            assert call_args[0][4] == "Jazz, Rock"  # New (sorted)
        
        def test_log_update_detects_field_addition(self, logger):
            """Test that adding a new field is logged."""
            audit_logger, mock_repo = logger
            
            old_data = {"title": "Song"}
            new_data = {"title": "Song", "artist": "New Artist"}
            
            audit_logger.log_update("Songs", 1, old_data, new_data)
            
            call_args = mock_repo.insert_change_logs.call_args[0][0]
            
            # Should log the new field
            assert len(call_args) == 1
            assert call_args[0][2] == "artist"
            assert call_args[0][3] is None  # Old value
            assert call_args[0][4] == "New Artist"  # New value
        
        def test_log_update_detects_field_removal(self, logger):
            """Test that removing a field is logged."""
            audit_logger, mock_repo = logger
            
            old_data = {"title": "Song", "artist": "Old Artist"}
            new_data = {"title": "Song"}
            
            audit_logger.log_update("Songs", 1, old_data, new_data)
            
            call_args = mock_repo.insert_change_logs.call_args[0][0]
            
            # Should log the removed field
            assert len(call_args) == 1
            assert call_args[0][2] == "artist"
            assert call_args[0][3] == "Old Artist"  # Old value
            assert call_args[0][4] is None  # New value
    
    class TestLogDelete:
        """Tests for log_delete method."""
        
        def test_log_delete_archives_snapshot(self, logger):
            """Test that delete logging archives full snapshot."""
            audit_logger, mock_repo = logger
            
            old_data = {
                "song_id": 42,
                "title": "Deleted Song",
                "artist": "Test Artist"
            }
            
            audit_logger.log_delete("Songs", 42, old_data)
            
            # Verify audit_repo.insert_deleted_record was called
            assert mock_repo.insert_deleted_record.called
            
            call_args = mock_repo.insert_deleted_record.call_args[0]
            
            # Verify arguments: (table_name, record_id, snapshot, batch_id)
            assert call_args[0] == "Songs"
            assert call_args[1] == 42
            
            # Verify snapshot is valid JSON
            snapshot = json.loads(call_args[2])
            assert snapshot["song_id"] == 42
            assert snapshot["title"] == "Deleted Song"
            assert snapshot["artist"] == "Test Artist"
        
        def test_log_delete_handles_empty_data(self, logger):
            """Test that empty data dict doesn't cause errors."""
            audit_logger, mock_repo = logger
            
            audit_logger.log_delete("Songs", 1, {})
            
            # Should not call repository
            assert not mock_repo.insert_deleted_record.called
        
        def test_log_delete_serializes_complex_data(self, logger):
            """Test that complex nested data is properly serialized."""
            audit_logger, mock_repo = logger
            
            old_data = {
                "album_id": 99,
                "tracks": [1, 2, 3],
                "metadata": {"year": 2024, "label": "Indie"}
            }
            
            audit_logger.log_delete("Albums", 99, old_data)
            
            call_args = mock_repo.insert_deleted_record.call_args[0]
            snapshot = json.loads(call_args[2])
            
            # Verify complex structures preserved
            assert snapshot["tracks"] == [1, 2, 3]
            assert snapshot["metadata"]["year"] == 2024
    
    class TestLogAction:
        """Tests for log_action method."""
        
        def test_log_action_with_all_params(self, logger):
            """Test logging action with all parameters."""
            audit_logger, mock_repo = logger
            
            details = {"file_count": 50, "duration": "5m"}
            
            audit_logger.log_action(
                action_type="IMPORT_COMPLETE",
                target_table="MediaSources",
                target_id=100,
                details=details,
                user_id="admin@example.com"
            )
            
            assert mock_repo.insert_action_log.called
            
            call_args = mock_repo.insert_action_log.call_args[0]
            
            assert call_args[0] == "IMPORT_COMPLETE"
            assert call_args[1] == "MediaSources"
            assert call_args[2] == 100
            
            # Verify details serialized to JSON
            details_json = json.loads(call_args[3])
            assert details_json["file_count"] == 50
            
            assert call_args[4] == "admin@example.com"
        
        def test_log_action_with_minimal_params(self, logger):
            """Test logging action with only required parameter."""
            audit_logger, mock_repo = logger
            
            audit_logger.log_action("SYSTEM_STARTUP")
            
            call_args = mock_repo.insert_action_log.call_args[0]
            
            assert call_args[0] == "SYSTEM_STARTUP"
            assert call_args[1] is None
            assert call_args[2] is None
            assert call_args[3] is None
            assert call_args[4] is None
        
        def test_log_action_with_none_details(self, logger):
            """Test that None details doesn't serialize to JSON."""
            audit_logger, mock_repo = logger
            
            audit_logger.log_action("TEST_ACTION", details=None)
            
            call_args = mock_repo.insert_action_log.call_args[0]
            assert call_args[3] is None  # Should remain None, not "null"
    
    class TestNormalization:
        """Tests for _normalize_dict helper method."""
        
        def test_normalize_primitives(self, logger):
            """Test that primitives are converted to strings."""
            audit_logger, _ = logger
            
            data = {
                "string": "text",
                "int": 42,
                "float": 3.14
            }
            
            result = audit_logger._normalize_dict(data)
            
            assert result["string"] == "text"
            assert result["int"] == "42"
            assert result["float"] == "3.14"
        
        def test_normalize_booleans(self, logger):
            """Test that booleans are converted to '1'/'0'."""
            audit_logger, _ = logger
            
            data = {
                "is_active": True,
                "is_deleted": False
            }
            
            result = audit_logger._normalize_dict(data)
            
            assert result["is_active"] == "1"
            assert result["is_deleted"] == "0"
        
        def test_normalize_lists(self, logger):
            """Test that lists are sorted and joined."""
            audit_logger, _ = logger
            
            data = {
                "genres": ["Rock", "Alternative", "Indie"],
                "empty_list": [],
                "with_none": ["A", None, "B"]
            }
            
            result = audit_logger._normalize_dict(data)
            
            # Should be sorted and joined
            assert result["genres"] == "Alternative, Indie, Rock"
            
            # Empty list should become empty string
            assert result["empty_list"] == ""
            
            # None values filtered out
            assert result["with_none"] == "A, B"
        
        def test_normalize_none_values(self, logger):
            """Test that None values remain None."""
            audit_logger, _ = logger
            
            data = {
                "field1": None,
                "field2": "value"
            }
            
            result = audit_logger._normalize_dict(data)
            
            assert result["field1"] is None
            assert result["field2"] == "value"
    
    class TestDiffCalculation:
        """Tests for _compute_diff helper method."""
        
        def test_diff_detects_simple_changes(self, logger):
            """Test that simple value changes are detected."""
            audit_logger, _ = logger
            
            old = {"title": "Old", "artist": "Same"}
            new = {"title": "New", "artist": "Same"}
            
            diffs = audit_logger._compute_diff(old, new)
            
            assert len(diffs) == 1
            assert "title" in diffs
            assert diffs["title"]["old"] == "Old"
            assert diffs["title"]["new"] == "New"
        
        def test_diff_detects_field_addition(self, logger):
            """Test that new fields are detected."""
            audit_logger, _ = logger
            
            old = {"title": "Song"}
            new = {"title": "Song", "artist": "New Artist"}
            
            diffs = audit_logger._compute_diff(old, new)
            
            assert len(diffs) == 1
            assert "artist" in diffs
            assert diffs["artist"]["old"] is None
            assert diffs["artist"]["new"] == "New Artist"
        
        def test_diff_detects_field_removal(self, logger):
            """Test that removed fields are detected."""
            audit_logger, _ = logger
            
            old = {"title": "Song", "artist": "Artist"}
            new = {"title": "Song"}
            
            diffs = audit_logger._compute_diff(old, new)
            
            assert len(diffs) == 1
            assert "artist" in diffs
            assert diffs["artist"]["old"] == "Artist"
            assert diffs["artist"]["new"] is None
        
        def test_diff_returns_empty_for_identical(self, logger):
            """Test that identical data returns no diffs."""
            audit_logger, _ = logger
            
            data = {"title": "Same", "artist": "Same"}
            
            diffs = audit_logger._compute_diff(data, data)
            
            assert len(diffs) == 0
        
        def test_diff_handles_list_order_changes(self, logger):
            """Test that list order doesn't matter (normalized)."""
            audit_logger, _ = logger
            
            old = {"genres": ["Rock", "Pop"]}
            new = {"genres": ["Pop", "Rock"]}  # Same items, different order
            
            diffs = audit_logger._compute_diff(old, new)
            
            # Should be no diff (both normalize to "Pop, Rock")
            assert len(diffs) == 0
        
        def test_diff_detects_boolean_changes(self, logger):
            """Test that boolean changes are detected."""
            audit_logger, _ = logger
            
            old = {"is_active": True}
            new = {"is_active": False}
            
            diffs = audit_logger._compute_diff(old, new)
            
            assert len(diffs) == 1
            assert diffs["is_active"]["old"] == "1"
            assert diffs["is_active"]["new"] == "0"
