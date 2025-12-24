"""Test configuration"""
import sys
import shutil
from pathlib import Path
import pytest
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC, COMM

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Path to the real test MP3 fixture
FIXTURE_MP3 = Path(__file__).parent / "fixtures" / "test.mp3"

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
        data=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
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
    from unittest.mock import patch
    with patch("src.business.services.metadata_service.MP3") as mock:
        yield mock

@pytest.fixture
def mock_id3():
    """Mock mutagen ID3"""
    from unittest.mock import patch
    with patch("src.business.services.metadata_service.ID3") as mock:
        yield mock

