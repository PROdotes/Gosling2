"""Test configuration"""
import sys
import shutil
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC, COMM

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Path to the real test MP3 fixture
FIXTURE_MP3 = Path(__file__).parent / "fixtures" / "test.mp3"

@pytest.fixture(autouse=True)
def silence_popups():
    """Silence all QMessageBox popups globally for non-interactive testing."""
    from PyQt6.QtWidgets import QMessageBox
    with patch('PyQt6.QtWidgets.QMessageBox.information'), \
         patch('PyQt6.QtWidgets.QMessageBox.warning'), \
         patch('PyQt6.QtWidgets.QMessageBox.critical'), \
         patch('PyQt6.QtWidgets.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
        yield

@pytest.fixture
def test_mp3(tmp_path):
    """Create a test MP3 file by copying the fixture"""
    if not FIXTURE_MP3.exists():
        pytest.skip(f"Test fixture not found: {FIXTURE_MP3}")
    
    mp3_path = tmp_path / "test.mp3"
    shutil.copy(FIXTURE_MP3, mp3_path)
    
    # Add basic ID3v2 tags
    audio = MP3(mp3_path)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text='Test Title'))
    audio.tags.add(TPE1(encoding=3, text='Test Artist'))
    audio.save(v1=0)
    
    return str(mp3_path)

# Path to the banana test MP3 fixture
FIXTURE_BANANA = Path(__file__).parent / "fixtures" / "bananas.mp3"

@pytest.fixture
def test_mp3_banana(tmp_path):
    """Create a banana test MP3 file by copying the fixture"""
    if not FIXTURE_BANANA.exists():
        pytest.skip(f"Test fixture not found: {FIXTURE_BANANA}")
    
    mp3_path = tmp_path / "bananas.mp3"
    shutil.copy(FIXTURE_BANANA, mp3_path)
    
    # Add distinct ID3v2 tags
    audio = MP3(mp3_path)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text='Banana Title'))
    audio.tags.add(TPE1(encoding=3, text='Banana Artist'))
    audio.save(v1=0)
    
    return str(mp3_path)

@pytest.fixture
def test_mp3_with_album_art(tmp_path):
    """MP3 with album art to test preservation"""
    if not FIXTURE_MP3.exists():
        pytest.skip(f"Test fixture not found: {FIXTURE_MP3}")
    
    mp3_path = tmp_path / "test_art.mp3"
    shutil.copy(FIXTURE_MP3, mp3_path)
    
    audio = MP3(mp3_path)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text='Test'))
    audio.tags.add(TPE1(encoding=3, text='Artist'))
    
    # Add minimal 1x1 PNG as album art
    audio.tags.add(APIC(
        encoding=3,
        mime='image/png',
        type=3,  # Cover (front)
        desc='Cover',
        data=b'\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01\\x08\\x06\\x00\\x00\\x00\\x1f\\x15\\xc4\\x89\\x00\\x00\\x00\\nIDATx\\x9cc\\x00\\x01\\x00\\x00\\x05\\x00\\x01\\r\\n-\\xb4\\x00\\x00\\x00\\x00IEND\\xaeB`\\x82'
    ))
    audio.save()
    
    return str(mp3_path)

@pytest.fixture
def test_mp3_with_comments(tmp_path):
    """MP3 with comments to test preservation"""
    if not FIXTURE_MP3.exists():
        pytest.skip(f"Test fixture not found: {FIXTURE_MP3}")
    
    mp3_path = tmp_path / "test_comments.mp3"
    shutil.copy(FIXTURE_MP3, mp3_path)
    
    audio = MP3(mp3_path)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text='Test'))
    audio.tags.add(COMM(encoding=3, lang='eng', desc='', text='Important comment'))
    audio.save()
    
    return str(mp3_path)

@pytest.fixture
def test_mp3_empty(tmp_path):
    """MP3 with no tags"""
    if not FIXTURE_MP3.exists():
        pytest.skip(f"Test fixture not found: {FIXTURE_MP3}")
    
    mp3_path = tmp_path / "test_empty.mp3"
    shutil.copy(FIXTURE_MP3, mp3_path)
    
    # Remove all tags
    audio = MP3(mp3_path)
    if audio.tags is not None:
        audio.delete()
    
    return str(mp3_path)

@pytest.fixture
def mock_mp3():
    """Mock mutagen MP3"""
    with patch("src.business.services.metadata_service.MP3") as mock:
        yield mock

@pytest.fixture
def mock_id3():
    """Mock mutagen ID3"""
    with patch("src.business.services.metadata_service.ID3") as mock:
        yield mock

@pytest.fixture
def mock_widget_deps():
    """Unified mock dependencies for LibraryWidget and related UI components"""
    deps = {
        'library_service': MagicMock(),
        'metadata_service': MagicMock(),
        'settings_manager': MagicMock(),
        'renaming_service': MagicMock(),
        'duplicate_scanner': MagicMock()
    }
    
    # Default settings to prevent common initialization crashes
    deps['settings_manager'].get_last_import_directory.return_value = ""
    deps['settings_manager'].get_column_visibility.return_value = {}
    deps['settings_manager'].get_column_layout.return_value = None
    deps['settings_manager'].get_type_filter.return_value = 0
    
    # Default library data (Empty but structured)
    deps['library_service'].get_all_songs.return_value = ([], [])
    
    return deps

@pytest.fixture
def library_widget(qtbot, mock_widget_deps):
    """Unified LibraryWidget fixture for general UI testing"""
    from src.presentation.widgets.library_widget import LibraryWidget
    deps = mock_widget_deps
    
    # Minimal struct for load_library not to crash
    deps['library_service'].get_all_songs.return_value = ([], [])
    
    widget = LibraryWidget(
        deps['library_service'], 
        deps['metadata_service'], 
        deps['settings_manager'],
        deps['renaming_service'],
        deps['duplicate_scanner']
    )
    qtbot.addWidget(widget)
    return widget

@pytest.fixture
def mock_library_service():
    """Mock library service for testing"""
    service = MagicMock()
    service.get_all_songs.return_value = ([], [])
    return service

@pytest.fixture
def mock_metadata_service():
    """Mock metadata service for testing"""
    return MagicMock()

@pytest.fixture
def mock_renaming_service():
    """Mock renaming service for testing"""
    return MagicMock()
