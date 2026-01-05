import pytest
import os
from unittest.mock import MagicMock, patch, mock_open
from src.business.services.conversion_service import ConversionService
from src.data.models.song import Song

class TestConversionService:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_settings = MagicMock()
        self.service = ConversionService(self.mock_settings)
        self.mock_settings.get_ffmpeg_path.return_value = "ffmpeg"
        self.mock_settings.get_conversion_bitrate.return_value = "320k"

    def test_convert_wav_to_mp3_success(self, tmp_path):
        # Create a dummy wav file
        wav_path = tmp_path / "test.wav"
        wav_path.write_text("dummy audio data")
        
        # Mock subprocess.Popen
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("Success", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # 1. Test CBR 320k
            self.mock_settings.get_conversion_bitrate.return_value = "320k"
            result = self.service.convert_wav_to_mp3(str(wav_path))
            
            expected_mp3 = str(wav_path.with_suffix(".mp3"))
            assert result == expected_mp3
            
            # Verify ffmpeg arguments
            args = mock_popen.call_args[0][0]
            assert "-b:a" in args
            assert "320k" in args
            assert "-q:a" not in args

    def test_convert_wav_to_mp3_vbr(self, tmp_path):
        # Create a dummy wav file
        wav_path = tmp_path / "test_vbr.wav"
        wav_path.write_text("dummy audio data")
        
        # Mock subprocess.Popen
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("Success", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # 2. Test VBR (V0)
            self.mock_settings.get_conversion_bitrate.return_value = "VBR (V0)"
            result = self.service.convert_wav_to_mp3(str(wav_path))
            
            # Verify ffmpeg arguments
            args = mock_popen.call_args[0][0]
            assert "-q:a" in args
            assert "0" in args
            assert "-b:a" not in args

    def test_convert_wav_to_mp3_ffmpeg_fail(self, tmp_path):
        wav_path = tmp_path / "test.wav"
        wav_path.write_text("dummy")
        
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "FFmpeg error")
            mock_process.returncode = 1
            mock_popen.return_value = mock_process
            
            result = self.service.convert_wav_to_mp3(str(wav_path))
            assert result is None

    def test_convert_wav_to_mp3_not_wav(self, tmp_path):
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("not a wav")
        
        result = self.service.convert_wav_to_mp3(str(txt_path))
        assert result is None

    def test_convert_wav_to_mp3_missing_file(self):
        result = self.service.convert_wav_to_mp3("non_existent_file.wav")
        assert result is None

    def test_sync_tags(self):
        # Mock MetadataService
        with patch("src.business.services.metadata_service.MetadataService.write_tags") as mock_write:
            mock_write.return_value = True
            
            song = Song(
                name="Surgical Title",
                performers=["Dr. Beat", "Nurse Rhythm"],
                album="The Clinic",
                recording_year=2025,
                tags=["Genre:Industrial"],
                publisher="Med Records"
            )
            
            result = self.service.sync_tags(song, "dummy.mp3")
            
            assert result is True
            # Verify it was called with the song and mock_write handled the path swap
            mock_write.assert_called_once_with(song)
            assert song.path != "dummy.mp3" # Should have been restored
