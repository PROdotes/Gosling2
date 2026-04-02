"""
Tests for src/services/converter.py — convert_to_mp3()

Mocks subprocess only. Real tmp files used for path/existence checks.
"""

from unittest.mock import patch, MagicMock

import pytest

from src.services.converter import convert_to_mp3


class TestConvertToMp3:
    def test_success_returns_mp3_path(self, tmp_path):
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"fake wav")
        mp3 = tmp_path / "track.mp3"

        def fake_run(cmd, **kwargs):
            mp3.write_bytes(b"fake mp3")
            return MagicMock(returncode=0)

        with patch("src.services.converter.subprocess.run", side_effect=fake_run):
            result = convert_to_mp3(wav)

        assert result == mp3, f"Expected {mp3}, got {result}"

    def test_success_deletes_source_wav(self, tmp_path):
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"fake wav")
        mp3 = tmp_path / "track.mp3"

        def fake_run(cmd, **kwargs):
            mp3.write_bytes(b"fake mp3")
            return MagicMock(returncode=0)

        with patch("src.services.converter.subprocess.run", side_effect=fake_run):
            convert_to_mp3(wav)

        assert (
            not wav.exists()
        ), "Source WAV should be deleted after successful conversion"

    def test_success_output_file_exists(self, tmp_path):
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"fake wav")
        mp3 = tmp_path / "track.mp3"

        def fake_run(cmd, **kwargs):
            mp3.write_bytes(b"fake mp3")
            return MagicMock(returncode=0)

        with patch("src.services.converter.subprocess.run", side_effect=fake_run):
            result = convert_to_mp3(wav)

        assert (
            result.exists()
        ), "Output MP3 file should exist after successful conversion"

    def test_nonzero_exit_raises_runtime_error(self, tmp_path):
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"fake wav")
        mp3 = tmp_path / "track.mp3"

        def fake_run(cmd, **kwargs):
            mp3.write_bytes(b"partial output")
            return MagicMock(returncode=1)

        with patch("src.services.converter.subprocess.run", side_effect=fake_run):
            with pytest.raises(RuntimeError):
                convert_to_mp3(wav)

    def test_nonzero_exit_cleans_up_partial_output(self, tmp_path):
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"fake wav")
        mp3 = tmp_path / "track.mp3"

        def fake_run(cmd, **kwargs):
            mp3.write_bytes(b"partial output")
            return MagicMock(returncode=1)

        with patch("src.services.converter.subprocess.run", side_effect=fake_run):
            with pytest.raises(RuntimeError):
                convert_to_mp3(wav)

        assert (
            not mp3.exists()
        ), "Partial MP3 output should be deleted on ffmpeg failure"

    def test_nonzero_exit_leaves_source_wav(self, tmp_path):
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"fake wav")
        mp3 = tmp_path / "track.mp3"

        def fake_run(cmd, **kwargs):
            mp3.write_bytes(b"partial output")
            return MagicMock(returncode=1)

        with patch("src.services.converter.subprocess.run", side_effect=fake_run):
            with pytest.raises(RuntimeError):
                convert_to_mp3(wav)

        assert wav.exists(), "Source WAV should be untouched on ffmpeg failure"

    def test_ffmpeg_not_found_raises_runtime_error(self, tmp_path):
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"fake wav")

        with patch(
            "src.services.converter.subprocess.run", side_effect=FileNotFoundError
        ):
            with pytest.raises(RuntimeError):
                convert_to_mp3(wav)

    def test_ffmpeg_not_found_leaves_source_wav(self, tmp_path):
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"fake wav")

        with patch(
            "src.services.converter.subprocess.run", side_effect=FileNotFoundError
        ):
            with pytest.raises(RuntimeError):
                convert_to_mp3(wav)

        assert (
            wav.exists()
        ), "Source WAV should be untouched when ffmpeg binary is missing"

    def test_output_missing_after_zero_exit_raises_runtime_error(self, tmp_path):
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"fake wav")

        with patch(
            "src.services.converter.subprocess.run",
            return_value=MagicMock(returncode=0),
        ):
            with pytest.raises(RuntimeError):
                convert_to_mp3(wav)

    def test_output_missing_after_zero_exit_leaves_source_wav(self, tmp_path):
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"fake wav")

        with patch(
            "src.services.converter.subprocess.run",
            return_value=MagicMock(returncode=0),
        ):
            with pytest.raises(RuntimeError):
                convert_to_mp3(wav)

        assert (
            wav.exists()
        ), "Source WAV should be untouched when output file is missing after conversion"
