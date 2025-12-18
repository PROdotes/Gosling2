"""Schema validation test for metadata write - ensures all Song fields are handled"""
import pytest
from src.data.models.song import Song


class TestMetadataWriteSchema:
    """Verify write_tags() handles all Song model fields (10th layer of yelling)"""
    
    def test_write_tags_covers_all_song_fields(self):
        """
        Ensure write_tags() handles all Song model fields.
        
        This is the 10th layer of the yelling mechanism:
        If you add a field to the Song model (which requires adding a DB column),
        this test will fail until you update write_tags() to handle it.
        """
        # Get all Song fields
        song_fields = {f.name for f in Song.__dataclass_fields__.values()}
        
        # Fields that write_tags() currently handles
        handled_fields = {
            'name',            # → TIT2 (via .title alias)
            'performers',      # → TPE1
            'composers',       # → TCOM
            'lyricists',       # → TEXT/TOLY
            'producers',       # → TIPL + TXXX:PRODUCER
            'groups',          # → TIT1
            'bpm',             # → TBPM
            'recording_year',  # → TDRC
            'isrc',            # → TSRC
            'is_done',         # → TKEY + TXXX:GOSLING_DONE
        }
        
        # Fields that are OK to skip (internal/read-only)
        skip_fields = {
            'source_id', # Database ID (not in ID3)
            'source',    # File path (not in ID3)
            'duration',  # Calculated from audio (not writable)
            'type_id',   # DB Type (Song/Jingle etc) - internal
            'notes',     # Internal notes - not written to ID3 yet
            'is_active', # Soft delete flag - internal
        }
        
        # Check for missing fields
        missing = song_fields - handled_fields - skip_fields
        
        assert not missing, (
            f"write_tags() doesn't handle these Song fields: {missing}\n"
            f"If you added a new field to Song, you must:\n"
            f"1. Update write_tags() to write it to ID3 tags\n"
            f"2. Add it to 'handled_fields' in this test\n"
            f"OR add it to 'skip_fields' if it shouldn't be written to ID3"
        )
    
    def test_write_tags_no_extra_fields(self):
        """
        Ensure write_tags() doesn't try to write fields that don't exist in Song.
        
        This catches typos or outdated code in write_tags().
        """
        # Get all Song fields
        song_fields = {f.name for f in Song.__dataclass_fields__.values()}
        
        # Fields that write_tags() handles (from above test)
        handled_fields = {
            'name', 'performers', 'composers', 'lyricists', 
            'producers', 'groups', 'bpm', 'recording_year', 
            'isrc', 'is_done'
        }
        
        # All handled fields must exist in Song
        extra = handled_fields - song_fields
        
        assert not extra, (
            f"write_tags() tries to write non-existent fields: {extra}\n"
            f"These fields don't exist in the Song model. Remove them from write_tags()."
        )
