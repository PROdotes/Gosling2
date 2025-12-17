"""Test fixtures for metadata service tests"""
import pytest
import os
from mutagen.mp3 import MP3, EasyMP3
from mutagen.id3 import ID3, TIT2, TPE1, TCOM, APIC, COMM


def _create_valid_mp3(path):
    """Create a minimal but valid MP3 file that mutagen can parse"""
    # Use a pre-generated minimal MP3 header + frame
    # This is a valid 1-frame MP3 (silence, ~417 bytes)
    mp3_data = (
        b'\xff\xfb\x90\x00'  # Frame sync + MPEG-1 Layer 3
        + b'\x00' * 413  # Padding to make valid frame
    )
    
    with open(path, 'wb') as f:
        f.write(mp3_data)


@pytest.fixture
def test_mp3(tmp_path):
    """Create a minimal valid MP3 file for testing"""
    mp3_path = tmp_path / "test.mp3"
    _create_valid_mp3(mp3_path)
    
    # Add ID3v2 tags
    try:
        audio = MP3(mp3_path)
        audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text='Test Title'))
        audio.tags.add(TPE1(encoding=3, text='Test Artist'))
        audio.save(v1=0)  # ID3v2 only
    except Exception as e:
        # If mutagen can't parse it, skip this test
        pytest.skip(f"Could not create test MP3: {e}")
    
    return str(mp3_path)


@pytest.fixture
def test_mp3_with_album_art(tmp_path):
    """MP3 with album art to test preservation"""
    mp3_path = tmp_path / "test_art.mp3"
    _create_valid_mp3(mp3_path)
    
    try:
        audio = MP3(mp3_path)
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
    except Exception as e:
        pytest.skip(f"Could not create test MP3 with album art: {e}")
    
    return str(mp3_path)


@pytest.fixture
def test_mp3_with_comments(tmp_path):
    """MP3 with comments to test preservation"""
    mp3_path = tmp_path / "test_comments.mp3"
    _create_valid_mp3(mp3_path)
    
    try:
        audio = MP3(mp3_path)
        audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text='Test'))
        audio.tags.add(COMM(encoding=3, lang='eng', desc='', text='Important comment'))
        audio.save()
    except Exception as e:
        pytest.skip(f"Could not create test MP3 with comments: {e}")
    
    return str(mp3_path)


@pytest.fixture
def test_mp3_empty(tmp_path):
    """MP3 with no tags"""
    mp3_path = tmp_path / "test_empty.mp3"
    _create_valid_mp3(mp3_path)
    
    return str(mp3_path)
