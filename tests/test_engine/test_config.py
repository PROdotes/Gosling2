import os
from unittest.mock import patch

from src.engine.config import get_downloads_folder


class TestGetDownloadsFolder:
    @patch("src.engine.config.os.name", "nt")
    @patch.dict(os.environ, {"USERPROFILE": "C:\\Users\\TestUser"}, clear=True)
    def test_nt_with_userprofile(self):
        result = get_downloads_folder()
        expected = os.path.join("C:\\Users\\TestUser", "Downloads")
        assert result == expected, f"Expected {expected}, got {result}"

    @patch("src.engine.config.os.name", "nt")
    @patch.dict(os.environ, {}, clear=True)
    def test_nt_without_userprofile(self):
        result = get_downloads_folder()
        expected = os.path.join("", "Downloads")
        assert result == expected, f"Expected {expected}, got {result}"

    @patch("src.engine.config.os.name", "posix")
    @patch.dict(os.environ, {"HOME": "/home/testuser"}, clear=True)
    def test_posix_with_home(self):
        result = get_downloads_folder()
        expected = os.path.join("/home/testuser", "Downloads")
        assert result == expected, f"Expected {expected}, got {result}"

    @patch("src.engine.config.os.name", "posix")
    @patch.dict(os.environ, {}, clear=True)
    def test_posix_without_home(self):
        result = get_downloads_folder()
        expected = os.path.join("", "Downloads")
        assert result == expected, f"Expected {expected}, got {result}"

    @patch("src.engine.config.os.name", "java")
    def test_unknown_os_returns_none(self):
        result = get_downloads_folder()
        assert result is None, f"Expected None, got {result}"
