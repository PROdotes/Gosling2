
import pytest
from unittest.mock import MagicMock
from src.business.services.audit_service import AuditService
from src.data.repositories.audit_repository import AuditRepository

class TestAuditService:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock(spec=AuditRepository)

    @pytest.fixture
    def service(self, mock_repo):
        return AuditService(audit_repository=mock_repo)

    def test_initialization_defaults(self):
        """Test service initializes with default repository if none provided."""
        # We can't easily check internal state without patching, but ensuring it doesn't crash is step 1
        svc = AuditService()
        assert isinstance(svc.audit_repo, AuditRepository)

    def test_get_recent_changes(self, service, mock_repo):
        """Test pass-through to repository."""
        mock_repo.get_change_log.return_value = [{"id": 1}]
        
        result = service.get_recent_changes(limit=50)
        
        mock_repo.get_change_log.assert_called_once_with(50)
        assert result == [{"id": 1}]

    def test_get_recent_actions(self, service, mock_repo):
        """Test pass-through to repository."""
        mock_repo.get_action_log.return_value = [{"action": "TEST"}]
        
        result = service.get_recent_actions(limit=25)
        
        mock_repo.get_action_log.assert_called_once_with(25)
        assert result == [{"action": "TEST"}]

    def test_get_unified_history(self, service, mock_repo):
        """Test unified history retrieval."""
        mock_repo.get_unified_log.return_value = [{"entry": "mixed"}]
        
        result = service.get_unified_history(limit=100)
        
        mock_repo.get_unified_log.assert_called_once_with(100)
        assert result == [{"entry": "mixed"}]

    def test_log_custom_action(self, service, mock_repo):
        """Test logging a custom high-level action."""
        details = {"key": "value"}
        
        service.log_custom_action(
            action_type="USER_EXPORT",
            details=details,
            target_table="Playlists",
            target_id=99
        )
        
        # Verify JSON serialization happens
        mock_repo.insert_action_log.assert_called_once()
        args, kwargs = mock_repo.insert_action_log.call_args
        
        assert args[0] == "USER_EXPORT"
        assert args[1] == "Playlists"
        assert args[2] == 99
        assert '{"key": "value"}' in args[3] # JSON string
        assert kwargs.get('user_id') == "SYSTEM"
