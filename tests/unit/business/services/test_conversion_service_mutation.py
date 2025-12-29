import pytest
import os
from unittest.mock import MagicMock, patch
from src.business.services.conversion_service import ConversionService

class TestConversionServiceMutation:
    """Robustness tests for ConversionService (Trust Boundary)."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_settings = MagicMock()
        self.service = ConversionService(self.mock_settings)

    def test_bitrate_injection_attempt(self, tmp_path):
        """Verify that shell injection via bitrate is blocked by list-style Popen."""
        wav_path = tmp_path / "test.wav"
        wav_path.write_text("dummy")
        
        # Malicious bitrate
        self.mock_settings.get_conversion_bitrate.return_value = "320k; rm -rf /"
        self.mock_settings.get_ffmpeg_path.return_value = "ffmpeg"
        
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            self.service.convert_wav_to_mp3(str(wav_path))
            
            # Verify the command was passed as a list, NOT a shell string
            args = mock_popen.call_args[0][0]
            assert isinstance(args, list)
            assert "320k; rm -rf /" in args # Passed as a single literal argument

    def test_ffmpeg_missing_binary(self, tmp_path):
        """Simulate FFmpeg not being in PATH."""
        wav_path = tmp_path / "test.wav"
        wav_path.write_text("dummy")
        
        self.mock_settings.get_ffmpeg_path.return_value = "non_existent_ffmpeg_binary"
        
        with patch("subprocess.Popen", side_effect=FileNotFoundError):
            result = self.service.convert_wav_to_mp3(str(wav_path))
            assert result is None # Should catch exception and return None

    def test_null_byte_path(self):
        """Check behavior with null byte in path (Standard robustness check)."""
        result = self.service.convert_wav_to_mp3("test\\x00.wav")
        assert result is None

    def test_sync_tags_exception_shield(self):
        """Ensure sync_tags doesn't crash if MetadataService explodes."""
        with patch("src.business.services.metadata_service.MetadataService.write_tags", side_effect=Exception("Metadata Boom")):
            result = self.service.sync_tags(MagicMock(), "dummy.mp3")
            assert result is False # Graceful failure
