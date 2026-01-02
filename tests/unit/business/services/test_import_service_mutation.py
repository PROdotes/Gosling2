
import pytest
from unittest.mock import MagicMock, patch
from src.business.services.import_service import ImportService

class TestImportServiceMutation:
    @pytest.fixture
    def service_deps(self):
        return {
            'library': MagicMock(),
            'metadata': MagicMock(),
            'scanner': MagicMock()
        }

    @pytest.fixture
    def import_service(self, service_deps):
        return ImportService(
            service_deps['library'],
            service_deps['metadata'],
            service_deps['scanner']
        )

    def test_import_non_existent_file(self, import_service):
        """Should return success=False if file does not exist (handled by hash helper)."""
        with patch('src.business.services.import_service.calculate_audio_hash', side_effect=FileNotFoundError("Missing")):
            success, sid, err = import_service.import_single_file("ghost.mp3")
            assert success is False
            assert "Missing" in err

    def test_import_corrupt_metadata(self, import_service, service_deps):
        """Should return success=False if metadata extraction crashes."""
        with patch('src.business.services.import_service.calculate_audio_hash', return_value="hash"):
            service_deps['scanner'].check_audio_duplicate.return_value = None
            service_deps['metadata'].extract_metadata.side_effect = Exception("Malformed ID3")
            
            success, sid, err = import_service.import_single_file("corrupt.mp3")
            
            assert success is False
            assert "Malformed ID3" in err

    def test_database_insert_failure(self, import_service, service_deps):
        """Should handle DB failures gracefully if add_file returns None."""
        with patch('src.business.services.import_service.calculate_audio_hash', return_value="hash"):
            service_deps['scanner'].check_audio_duplicate.return_value = None
            service_deps['scanner'].check_isrc_duplicate.return_value = None
            service_deps['metadata'].extract_metadata.return_value = MagicMock(isrc=None)
            service_deps['library'].add_file.return_value = None
            
            success, sid, err = import_service.import_single_file("fail.mp3")
            
            assert success is False
            assert "Failed to create database record" in err

    def test_null_file_path(self, import_service):
        """Chaos Monkey: passing None as path."""
        success, sid, err = import_service.import_single_file(None)
        assert success is False
        assert err is not None
