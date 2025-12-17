# Metadata Write Implementation TODO

## Overview
Implement `MetadataService.write_tags(song: Song)` to write Song object data to MP3 ID3 tags using mutagen.

## Critical Safety Requirements

### 🚨 **MUST NOT:**
1. **Delete existing frames** that Gosling doesn't manage (e.g., APIC album art, COMM comments)
2. **Overwrite non-empty fields** with empty values (preserve existing data if Song field is None/empty)
3. **Corrupt the file** on write failure (use atomic write or backup)
4. **Write invalid data** (validate before writing)

### ✅ **MUST:**
1. **Preserve unmanaged frames** (only update frames Gosling knows about)
2. **Handle write failures gracefully** (return False, don't crash)
3. **Validate Song data** before writing (e.g., year range, ISRC format)
4. **Test with real MP3 files** (not just mocks)
5. **Handle ID3v1 and ID3v2** properly (see ID3 Version Handling below)

## ID3 Version Handling

### Background
- **ID3v1:** Legacy format (128 bytes, limited fields, no Unicode)
- **ID3v2:** Modern format (unlimited fields, Unicode, extensible)
- **Both can coexist** in the same file!

### Current Behavior (Reading)
- `extract_from_mp3()` uses `ID3(path)` which reads **ID3v2 only**
- If no ID3v2 exists, mutagen may fall back to ID3v1
- **Risk:** Missing data if file has ID3v1 but no ID3v2

### Recommended Strategy (Writing)
1. **Always write ID3v2** (modern standard)
2. **Preserve ID3v1 if it exists** (don't create new v1 tags)
3. **Use `audio.save(v1=1)`** to preserve existing v1
   - `v1=0`: Don't write ID3v1 (deletes it)
   - `v1=1`: Write ID3v1 only if it already exists (recommended)
   - `v1=2`: Always write ID3v1 (creates new v1 tags)

### Implementation
```python
# When saving:
audio.save(v1=1)  # Preserve existing ID3v1, don't create new
```

### Testing
- [ ] **test_write_tags_id3v1_only** - File with only ID3v1 tags
- [ ] **test_write_tags_id3v2_only** - File with only ID3v2 tags
- [ ] **test_write_tags_both_versions** - File with both v1 and v2
- [ ] **test_write_tags_creates_v2** - File with no tags gets ID3v2
- [ ] **test_write_tags_preserves_v1** - Existing ID3v1 not deleted

## Test Fixtures (MP3 Generation)

### Strategy: Generate MP3s Programmatically
To avoid copyright issues and external dependencies, generate minimal valid MP3 files using mutagen in test fixtures.

### Implementation
```python
# tests/conftest.py or test_metadata_service.py

import pytest
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC

@pytest.fixture
def test_mp3(tmp_path):
    """Create a minimal valid MP3 file for testing"""
    mp3_path = tmp_path / "test.mp3"
    
    # Write minimal valid MP3 frames (silence)
    with open(mp3_path, 'wb') as f:
        # MPEG-1 Layer 3, 128kbps, 44.1kHz, mono
        f.write(b'\xff\xfb\x90\x00' * 100)
    
    # Add ID3v2 tags
    audio = MP3(mp3_path)
    audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text='Test Title'))
    audio.tags.add(TPE1(encoding=3, text='Test Artist'))
    audio.save(v1=0)  # ID3v2 only
    
    return str(mp3_path)

@pytest.fixture
def test_mp3_with_album_art(tmp_path):
    """MP3 with album art to test preservation"""
    mp3_path = tmp_path / "test_art.mp3"
    
    with open(mp3_path, 'wb') as f:
        f.write(b'\xff\xfb\x90\x00' * 100)
    
    audio = MP3(mp3_path)
    audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text='Test'))
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
def test_mp3_id3v1_only(tmp_path):
    """MP3 with only ID3v1 tags"""
    mp3_path = tmp_path / "test_v1.mp3"
    
    with open(mp3_path, 'wb') as f:
        f.write(b'\xff\xfb\x90\x00' * 100)
    
    audio = MP3(mp3_path)
    audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text='Test'))
    audio.save(v1=2)  # Force ID3v1
    
    # Remove ID3v2 to leave only v1
    audio = MP3(mp3_path)
    audio.delete()
    
    return str(mp3_path)
```

**Benefits:**
- ✅ No copyright issues (generated, not real music)
- ✅ No external tools needed (pure Python)
- ✅ Generated fresh for each test (in `tmp_path`)
- ✅ No files committed to git
- ✅ Fast (< 1ms to generate)


## Implementation Checklist

### 1. Core Implementation (`metadata_service.py`)
- [ ] Load existing ID3 tags (preserve unmanaged frames)
- [ ] Map Song fields to ID3 frames:
  - [ ] `title` → `TIT2`
  - [ ] `performers` → `TPE1` (join with `;` or multiple frames)
  - [ ] `composers` → `TCOM`
  - [ ] `lyricists` → `TEXT` (or `TOLY`)
  - [ ] `producers` → `TIPL` (role="producer") + `TXXX:PRODUCER`
  - [ ] `groups` → `TIT1`
  - [ ] `bpm` → `TBPM`
  - [ ] `recording_year` → `TDRC` (format: "YYYY")
  - [ ] `isrc` → `TSRC`
  - [ ] `is_done` → `TKEY` ("true"/" ") + `TXXX:GOSLING_DONE` ("1"/"0")
- [ ] Handle empty/None values (skip or preserve existing)
- [ ] Save file with error handling
- [ ] Return True on success, False on failure

### 2. Data Validation
- [ ] Year: 1860 ≤ year ≤ current_year + 1
- [ ] ISRC: Valid format (CC-XXX-YY-NNNNN)
- [ ] BPM: Positive integer
- [ ] Lists: Non-empty strings only

### 3. Unit Tests (`test_metadata_service.py`)

#### Test Cases:
- [ ] **test_write_tags_basic** - Write all fields to new MP3
- [ ] **test_write_tags_preserves_album_art** - APIC frame not deleted
- [ ] **test_write_tags_preserves_comments** - COMM frame not deleted
- [ ] **test_write_tags_preserves_unknown_frames** - Custom TXXX frames preserved
- [ ] **test_write_tags_updates_existing** - Overwrite existing TIT2, TPE1, etc.
- [ ] **test_write_tags_handles_empty_fields** - None/empty lists don't delete existing data
- [ ] **test_write_tags_handles_lists** - Multiple performers/composers
- [ ] **test_write_tags_is_done_true** - TKEY="true", TXXX:GOSLING_DONE="1"
- [ ] **test_write_tags_is_done_false** - TKEY=" ", TXXX:GOSLING_DONE="0"
- [ ] **test_write_tags_invalid_file** - Returns False for non-MP3
- [ ] **test_write_tags_file_locked** - Returns False if file in use
- [ ] **test_write_tags_roundtrip** - Write then read, data matches
- [ ] **test_write_tags_validation_year** - Rejects invalid years
- [ ] **test_write_tags_validation_isrc** - Rejects invalid ISRC

### 4. Integration Tests
- [ ] Create test MP3 with album art
- [ ] Write metadata
- [ ] Verify album art still exists
- [ ] Verify all Gosling fields updated
- [ ] Verify file still playable

### 5. Edge Cases
- [ ] Empty Song object (all fields None)
- [ ] Song with only some fields populated
- [ ] Very long strings (title > 255 chars)
- [ ] Unicode characters (emoji, special chars)
- [ ] File with no existing ID3 tags
- [ ] File with corrupted ID3 tags

## Example Implementation Pattern

```python
@staticmethod
def write_tags(song: Song) -> bool:
    """
    Write metadata from Song object to MP3 file.
    Preserves existing frames not managed by Gosling.
    Returns True on success, False on failure.
    """
    try:
        # Load file
        audio = MP3(song.path, ID3=ID3)
        
        # Ensure tags exist
        if audio.tags is None:
            audio.add_tags()
        
        # ONLY update frames Gosling manages
        # DO NOT delete frames we don't know about (APIC, COMM, etc.)
        
        # Update title (only if not None)
        if song.title is not None:
            audio.tags.delall('TIT2')  # Remove old
            audio.tags.add(TIT2(encoding=3, text=song.title))
        
        # Update performers (handle list)
        if song.performers:
            audio.tags.delall('TPE1')
            audio.tags.add(TPE1(encoding=3, text=song.performers))
        
        # ... (repeat for all fields)
        
        # Update is_done (dual mode)
        audio.tags.delall('TKEY')
        audio.tags.delall('TXXX:GOSLING_DONE')
        audio.tags.add(TKEY(encoding=3, text='true' if song.is_done else ' '))
        audio.tags.add(TXXX(encoding=3, desc='GOSLING_DONE', text='1' if song.is_done else '0'))
        
        # Save
        audio.save()
        return True
        
    except Exception as e:
        print(f"Error writing tags to {song.path}: {e}")
        return False
```

## Testing Strategy

1. **Create test fixtures** with real MP3 files (with album art, comments)
2. **Test preservation** - Verify unmanaged frames survive write
3. **Test roundtrip** - Write → Read → Verify data matches
4. **Test edge cases** - Empty, None, invalid data
5. **Manual verification** - Open in iTunes/VLC to verify tags

## Definition of Done

- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Manual verification with real MP3 files
- [ ] Album art preserved after write
- [ ] Comments preserved after write
- [ ] No data loss on write failure
- [ ] Code reviewed for safety

## Notes

- Use `encoding=3` (UTF-8) for all text frames
- Use `delall()` before `add()` to avoid duplicates
- Don't use `tags.clear()` - it deletes everything!
- Test with files that have album art (APIC frame)
- Test with files that have comments (COMM frame)
