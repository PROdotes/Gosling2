import pytest
from src.core import yellberus
from src.core.yellberus import FieldType

def test_registry_has_fields():
    """Ensure the registry is populated."""
    assert len(yellberus.FIELDS) > 0
    assert yellberus.get_field("title") is not None
    assert yellberus.get_field("recording_year") is not None

def test_get_field_lookup():
    """Test looking up fields by name."""
    field = yellberus.get_field("recording_year")
    assert field.name == "recording_year"
    assert field.ui_header == "Year"
    assert field.field_type == FieldType.INTEGER
    assert field.filterable is True
    
    # Non-existent field
    assert yellberus.get_field("non_existent_ghost_field") is None

def test_visible_fields():
    """Test retrieving only visible fields."""
    visible = yellberus.get_visible_fields()
    
    # Check that visible fields are present
    assert any(f.name == "title" for f in visible)
    assert any(f.name == "recording_year" for f in visible)
    
    # Check that invisible fields are NOT present
    assert not any(f.name == "file_id" for f in visible)
    assert not any(f.name == "type_id" for f in visible)

def test_filterable_fields():
    """Test retrieving only filterable fields."""
    filterable = yellberus.get_filterable_fields()
    
    # Check filterable fields
    assert any(f.name == "recording_year" for f in filterable)
    assert any(f.name == "unified_artist" for f in filterable)  # T-17: unified_artist replaces performers/groups
    
    # Check non-filterable fields (including now-hidden performers/groups)
    assert not any(f.name == "title" for f in filterable)
    assert not any(f.name == "duration" for f in filterable)
    assert not any(f.name == "performers" for f in filterable)  # Hidden, use unified_artist
    assert not any(f.name == "groups" for f in filterable)  # Hidden, use unified_artist

def test_decade_grouper():
    """Test the decade grouping logic."""
    grouper = yellberus.decade_grouper
    
    assert grouper(1984) == "1980s"
    assert grouper(1990) == "1990s"
    assert grouper("2023") == "2020s" # Should handle string input
    assert grouper(None) == "Unknown"
    assert grouper("Not a year") == "Unknown"

def test_field_properties():
    """Test specific properties of a complex field."""
    field = yellberus.get_field("performers")
    assert field.min_length == 1
    assert field.field_type == FieldType.LIST
    assert field.db_column == "Performers"

def test_validate_schema():
    """Test that schema validation passes."""
    # Should not raise
    yellberus.validate_schema()

def test_portable_flag():
    """Test that portable vs local-only fields are marked correctly."""
    # Portable fields can travel with MP3 (have mappings in JSON)
    performers = yellberus.get_field("performers")
    assert performers.portable is True
    
    # Local fields are station-specific (no ID3 mapping needed)
    file_id = yellberus.get_field("file_id")
    assert file_id.portable is False
    
    is_done = yellberus.get_field("is_done")
    assert is_done.portable is False

def test_row_to_tagged_tuples():
    """Test Yellberus returns tagged tuples for Song."""
    # Create a mock row matching FIELDS order (17 columns):
    # 0:path, 1:file_id, 2:type_id, 3:notes, 4:isrc, 5:is_active,
    # 6:producers, 7:lyricists, 8:duration, 9:title,
    # 10:is_done, 11:bpm, 12:recording_year, 13:performers, 14:composers, 15:groups, 16:unified_artist
    row = (
        "/path",           # 0: path
        1,                 # 1: file_id
        1,                 # 2: type_id
        None,              # 3: notes
        "ISRC123",         # 4: isrc
        True,              # 5: is_active
        None,              # 6: producers
        None,              # 7: lyricists
        180,               # 8: duration
        "Title",           # 9: title
        False,             # 10: is_done
        120,               # 11: bpm
        2024,              # 12: recording_year
        "Artist",          # 13: performers
        "Composer",        # 14: composers
        "Group",           # 15: groups
        "Unified",         # 16: unified_artist
    )
    
    tagged = yellberus.row_to_tagged_tuples(row)
    
    # Should have 17 tuples
    assert len(tagged) == 17
    
    # Portable fields should have ID3 frame tags
    assert ("Title", "TIT2") in tagged
    assert (["Artist"], "TPE1") in tagged  # List type is split
    
    # Local fields should have underscore prefix
    assert (1, "_file_id") in tagged
    assert (False, "_is_done") in tagged

def test_song_from_row():
    """Test Song.from_row uses tagged tuples and JSON lookup."""
    from src.data.models.song import Song
    
    # Row matching current FIELDS order (17 columns)
    row = (
        "/music/test.mp3", # 0: path
        1,                 # 1: file_id
        1,                 # 2: type_id
        None,              # 3: notes
        "USMV123",         # 4: isrc
        True,              # 5: is_active
        None,              # 6: producers
        None,              # 7: lyricists
        200,               # 8: duration
        "Test Song",       # 9: title
        True,              # 10: is_done
        128,               # 11: bpm
        2024,              # 12: recording_year
        "Artist 1, Artist 2",  # 13: performers
        "Bach",            # 14: composers
        "Test Group",      # 15: groups
        "Unified Artist",  # 16: unified_artist
    )
    
    song = Song.from_row(row)
    
    # Check mappings worked
    assert song.source_id == 1
    assert song.name == "Test Song"
    assert song.performers == ["Artist 1", "Artist 2"]
    assert song.composers == ["Bach"]
    assert song.bpm == 128
    assert song.recording_year == 2024
    assert song.isrc == "USMV123"
    assert song.is_done is True
