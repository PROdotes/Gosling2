
import pytest
from unittest.mock import MagicMock, patch
from src.business.services.import_service import ImportService
from src.data.models.song import Song

class TestImportServiceLogic:
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

    def test_import_single_file_success(self, import_service, service_deps):
        """Happy path: File is hashed, metadata extracted, added to DB and tagged."""
        test_path = "path/to/song.mp3"
        fake_song = Song(name="Test Title", isrc="US123")
        
        # Setup mocks
        with patch('src.business.services.import_service.calculate_audio_hash', return_value="fake_hash"):
            service_deps['scanner'].check_audio_duplicate.return_value = None
            service_deps['metadata'].extract_metadata.return_value = fake_song
            service_deps['scanner'].check_isrc_duplicate.return_value = None
            service_deps['library'].add_file.return_value = 101
            
            # Mock tag_repo property
            mock_tag_repo = MagicMock()
            service_deps['library'].tag_repo = mock_tag_repo
            import_service.tag_repo = mock_tag_repo

            success, sid, err = import_service.import_single_file(test_path)

            assert success is True
            assert sid == 101
            assert err is None
            
            # Verify database updates
            service_deps['library'].update_song.assert_called_once()
            mock_tag_repo.add_tag_to_source.assert_called_with(101, "Unprocessed", category="Status")

    def test_skip_audio_duplicate(self, import_service, service_deps):
        """Import should fail if audio hash already exists."""
        with patch('src.business.services.import_service.calculate_audio_hash', return_value="existing_hash"):
            service_deps['scanner'].check_audio_duplicate.return_value = MagicMock()
            
            success, sid, err = import_service.import_single_file("dup.mp3")
            
            assert success is False
            assert "Duplicate audio found" in err
            service_deps['library'].add_file.assert_not_called()

    def test_skip_isrc_duplicate(self, import_service, service_deps):
        """Import should fail if ISRC already exists."""
        fake_song = Song(name="Title", isrc="EXISTING_ISRC")
        
        with patch('src.business.services.import_service.calculate_audio_hash', return_value="unique_hash"):
            service_deps['scanner'].check_audio_duplicate.return_value = None
            service_deps['metadata'].extract_metadata.return_value = fake_song
            service_deps['scanner'].check_isrc_duplicate.return_value = MagicMock()
            
            success, sid, err = import_service.import_single_file("dup_isrc.mp3")
            
            assert success is False
            assert "Duplicate ISRC found" in err

    def test_scan_directory_recursive(self, import_service):
        """Discovery phase should find audio files in nested folders."""
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [
                ('/root', ('subdir',), ('song1.mp3', 'image.jpg')),
                ('/root/subdir', (), ('song2.flac', 'doc.txt'))
            ]
            
            files = import_service.scan_directory_recursive('/root')
            
            assert len(files) == 2
            assert any('song1.mp3' in f for f in files)
            assert any('song2.flac' in f for f in files)
