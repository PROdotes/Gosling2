
import pytest
import os
from unittest.mock import MagicMock, patch, PropertyMock
from src.business.services.renaming_service import RenamingService
from src.data.models.song import Song

# Mock Song Data
@pytest.fixture
def mock_song():
    song = MagicMock(spec=Song)
    # Configure as instance attributes
    song.unified_artist = "Logic Boys"
    song.title = "Algorithmic Beats"
    song.year = "2024"
    song.genre = "Techno"
    song.bpm = 120
    # Use generic path based on OS sep
    song.path = os.path.join("music", "incoming", "random_file.mp3")
    return song

@pytest.fixture
def service():
    # Mock SettingsManager
    settings_mock = MagicMock()
    # Fix method name: get_rename_pattern, not get_renaming_pattern
    settings_mock.get_rename_pattern.return_value = "{Genre}/{Year}/{Artist} - {Title}.mp3"
    # Use generic root
    settings_mock.get_root_directory.return_value = os.path.join("music", "library")
    
    return RenamingService(settings_mock)

def test_calculate_target_path(service, mock_song):
    """Verify standard pattern generation."""
    path = service.calculate_target_path(mock_song)
    
    # Expected: music/library/Techno/2024/Logic Boys - Algorithmic Beats.mp3
    expected = os.path.join("music", "library", "Techno", "2024", "Logic Boys - Algorithmic Beats.mp3")
    assert os.path.normpath(path) == os.path.normpath(expected)

def test_calculate_path_sanitization(service, mock_song):
    """Verify illegal chars are stripped."""
    mock_song.title = "Beats / With : Bad > Chars"
    path = service.calculate_target_path(mock_song)
    
    filename = "Logic Boys - Beats  With  Bad  Chars.mp3"
    expected = os.path.join("music", "library", "Techno", "2024", filename)
    assert os.path.normpath(path) == os.path.normpath(expected)

def test_calculate_path_missing_metadata(service, mock_song):
    """Verify fallback for missing Genre/Year."""
    mock_song.year = None
    mock_song.genre = ""
    
    path = service.calculate_target_path(mock_song)
    
    expected = os.path.join("music", "library", "Uncategorized", "0000", "Logic Boys - Algorithmic Beats.mp3")
    assert os.path.normpath(path) == os.path.normpath(expected)

def test_check_conflict_true(service):
    """Verify conflict detection when file exists."""
    target_path = os.path.join("music", "library", "Techno", "2024", "Logic Boys - Algorithmic Beats.mp3")
    
    with patch("os.path.exists", return_value=True):
        assert service.check_conflict(target_path) is True

def test_check_conflict_false(service):
    """Verify conflict detection when file is free."""
    target_path = os.path.join("music", "library", "New", "Song.mp3")
    
    with patch("os.path.exists", return_value=False):
        assert service.check_conflict(target_path) is False

def test_rename_song_success(service, mock_song):
    """Verify successful move."""
    target = os.path.join("music", "library", "Techno", "2024", "Logic Boys - Algorithmic Beats.mp3")
    
    with patch("os.path.exists") as mock_exists, \
         patch("os.makedirs") as mock_mkdirs, \
         patch("shutil.move") as mock_move:
        
        def exists_side_effect(path):
            if path == target: return False 
            if path == mock_song.path: return True
            return False
            
        mock_exists.side_effect = exists_side_effect
        
        # Capture source path before modification
        src_path = mock_song.path

        # Execute
        success = service.rename_song(mock_song, target_path=target)
        
        assert success is True
        mock_mkdirs.assert_called_once()
        mock_move.assert_called_once_with(src_path, target)
        assert mock_song.path == target

def test_rename_song_conflict_fails(service, mock_song):
    """Verify rename fails if target exists (STRICT FAIL)."""
    target = os.path.join("music", "library", "Techno", "2024", "Logic Boys - Algorithmic Beats.mp3")
    
    with patch("os.path.exists") as mock_exists, \
         patch("shutil.move") as mock_move:
        
        def exists_side_effect(path):
            if path == target: return True 
            if path == mock_song.path: return True 
            return False
        mock_exists.side_effect = exists_side_effect
        
        success = service.rename_song(mock_song, target_path=target)
        
        assert success is False
        mock_move.assert_not_called()
