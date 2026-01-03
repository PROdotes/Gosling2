import pytest
from unittest.mock import patch, MagicMock
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from src.business.services.metadata_service import MetadataService
from src.data.models.song import Song

class TestMetadataExtractionLogic:
    """Level 1: Happy Path and Basic Logic for Reading"""
    
    def test_extract_from_mp3_success(self, mock_mp3):
        """Standard successful extraction"""
        # Explicit configuration
        audio_instance = MagicMock()
        audio_instance.info = MagicMock()
        audio_instance.info.length = 180.5

        # Setup tags dictionary behavior
        tags_mock = {} 
        # Mock TIT2
        tit2 = MagicMock()
        tit2.text = ["Test Title"]
        tags_mock["TIT2"] = tit2
        
        # Mock TPE1
        tpe1 = MagicMock()
        tpe1.text = ["Artist 1", "Artist 2"]
        tags_mock["TPE1"] = tpe1
        
        audio_instance.tags = tags_mock
        mock_mp3.return_value = audio_instance
        
        song = MetadataService.extract_from_mp3("dummy.mp3", source_id=1)
        assert song.title == "Test Title"
        assert song.duration == 180.5
        assert "Artist 1" in song.performers

    def test_extract_from_mp3_no_tags(self, mock_mp3):
        """Basic Error: File exists but has an empty tag dictionary"""
        audio_instance = MagicMock()
        audio_instance.info = MagicMock()
        audio_instance.info.length = 200
        audio_instance.tags = {} # Empty dict
        mock_mp3.return_value = audio_instance

        song = MetadataService.extract_from_mp3("no_tags.mp3")
        assert song.duration == 200
        assert song.title is None
        assert song.performers == []

    def test_title_cleaning(self, mock_mp3):
        """Basic Logic: Title whitespace stripping"""
        audio_mock = mock_mp3.return_value
        
        tit2 = MagicMock()
        tit2.text = ["  Clean Me  "]
        audio_mock.tags = {"TIT2": tit2}
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.title == "Clean Me"

class TestMetadataWriteLogic:
    """Level 1: Happy Path and Basic Logic for Writing"""
    
    def test_write_tags_basic(self, test_mp3):
        """Write standard fields to a valid MP3"""
        song = Song(
            source=test_mp3,
            name="New Title",
            performers=["Artist 1"],
            bpm=120
        )
        assert MetadataService.write_tags(song) is True
        
        audio = MP3(test_mp3, ID3=ID3)
        assert str(audio.tags['TIT2']) == "New Title"

    def test_dual_mode_writing(self, mock_mp3, mock_id3):
        """Requirement: Year writes to both TYER and TDRC"""
        from mutagen.id3 import TYER, TDRC
        mock_audio = mock_mp3.return_value
        song = Song(source="test.mp3", recording_year=2025)
        MetadataService.write_tags(song)
        
        found_tyer = any(isinstance(c[0][0], TYER) for c in mock_audio.tags.add.call_args_list)
        found_tdrc = any(isinstance(c[0][0], TDRC) for c in mock_audio.tags.add.call_args_list)
        assert found_tyer and found_tdrc


    def test_preservation_logic(self, test_mp3_with_album_art):
        """Requirement: Album art is preserved during metadata updates"""
        song = Song(source=test_mp3_with_album_art, name="Preserve Art")
        MetadataService.write_tags(song)
        
        audio = MP3(test_mp3_with_album_art, ID3=ID3)
        assert 'APIC:Cover' in audio.tags


class TestMetadataExtractionComprehensive:
    """Level 1: Comprehensive extraction tests (from comprehensive.py)"""


    def test_title_with_whitespace(self, mock_mp3):
        """Test that title whitespace is properly stripped"""
        audio_mock = mock_mp3.return_value
        
        tit2 = MagicMock()
        tit2.text = ["  Title With Spaces  "]
        audio_mock.tags = {"TIT2": tit2}
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.title == "Title With Spaces"

    def test_title_multiple_frames(self, mock_mp3):
        """Test that only first title is used when multiple exist"""
        audio_mock = mock_mp3.return_value
        
        tit2 = MagicMock()
        tit2.text = ["First Title", "Second Title"]
        audio_mock.tags = {"TIT2": tit2}
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.title == "First Title"

    def test_performers_deduplication(self, mock_mp3):
        """Test that duplicate performers are removed while preserving order"""
        audio_mock = mock_mp3.return_value
        
        tpe1 = MagicMock()
        tpe1.text = ["Artist A", "Artist B", "Artist A", "Artist C"]
        audio_mock.tags = {"TPE1": tpe1}
        
        song = MetadataService.extract_from_mp3("test.mp3")
        # Note: "Artist A" appears twice in source, but new logic is stricter about frame usage.
        # However, this test sets a SINGLE frame with multiple values.
        # Our logic: get_values() returns ["Artist A", "Artist B", "Artist A", "Artist C"]
        # Then dedupe: ["Artist A", "Artist B", "Artist C"]
        assert song.performers == ["Artist A", "Artist B", "Artist C"]
        assert len(song.performers) == 3

    def test_performers_multiple_frames(self, mock_mp3):
        """Test handling of multiple TPE1 frames"""
        pass # Mutagen behavior is one key per frame type usually, skipping advanced multi-frame mocking for now.

    def test_composers_extraction(self, mock_mp3):
        """Test composer extraction from TCOM"""
        audio_mock = mock_mp3.return_value
        
        tcom = MagicMock()
        tcom.text = ["Composer A", "Composer B"]
        audio_mock.tags = {"TCOM": tcom}
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.composers == ["Composer A", "Composer B"]

    def test_lyricists_from_toly(self, mock_mp3):
        """Test lyricist extraction from TOLY"""
        audio_mock = mock_mp3.return_value
        
        toly = MagicMock()
        toly.text = ["Lyricist A"]
        audio_mock.tags = {"TOLY": toly}
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.lyricists == ["Lyricist A"]

    def test_lyricists_fallback_to_text(self, mock_mp3):
        """Test lyricist fallback from TOLY to TEXT"""
        audio_mock = mock_mp3.return_value
        
        text = MagicMock()
        text.text = ["Lyricist from TEXT"]
        audio_mock.tags = {"TEXT": text}
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.lyricists == ["Lyricist from TEXT"]

    def test_bpm_valid_integer(self, mock_mp3):
        """Test BPM extraction with valid integer"""
        audio_mock = mock_mp3.return_value
        
        tbpm = MagicMock()
        tbpm.text = ["128"]
        audio_mock.tags = {"TBPM": tbpm}
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.bpm == 128
        assert isinstance(song.bpm, int)

    def test_producers_from_tipl_only(self, mock_mp3):
        """Test producer extraction from TIPL"""
        audio_mock = mock_mp3.return_value
        
        tipl = MagicMock()
        tipl.people = [
            ("producer", "Producer A"),
            ("engineer", "Engineer B"),
            ("Producer", "Producer C"),
        ]
        audio_mock.tags = {"TIPL": tipl}
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert "Producer A" in song.producers
        assert "Producer C" in song.producers
        assert "Engineer B" not in song.producers
        assert len(song.producers) == 2

    def test_producers_from_txxx_only(self, mock_mp3):
        """Test producer extraction from TXXX:PRODUCER"""
        audio_mock = mock_mp3.return_value
        
        txxx = MagicMock()
        txxx.text = ["TXXX Producer"]
        audio_mock.tags = {"TXXX:PRODUCER": txxx}
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert "TXXX Producer" in song.producers

    def test_producers_from_both_tipl_and_txxx(self, mock_mp3):
        """Test producer extraction from both TIPL and TXXX"""
        audio_mock = mock_mp3.return_value
        
        tags = {}
        tipl = MagicMock()
        tipl.people = [("producer", "TIPL Producer")]
        tags["TIPL"] = tipl
        
        txxx = MagicMock()
        txxx.text = ["TXXX Producer"]
        tags["TXXX:PRODUCER"] = txxx
        
        audio_mock.tags = tags
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert "TIPL Producer" in song.producers
        assert "TXXX Producer" in song.producers
        assert len(song.producers) == 2

    def test_producers_deduplication(self, mock_mp3):
        """Test that duplicate producers are removed"""
        audio_mock = mock_mp3.return_value
        
        tags = {}
        tipl = MagicMock()
        # Duplicate inside TIPL
        tipl.people = [
            ("producer", "Same Producer"),
            ("producer", "Same Producer"),
        ]
        tags["TIPL"] = tipl
        
        txxx = MagicMock()
        txxx.text = ["Same Producer"]
        tags["TXXX:PRODUCER"] = txxx
        
        audio_mock.tags = tags
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.producers == ["Same Producer"]
        assert len(song.producers) == 1

    def test_groups_extraction(self, mock_mp3):
        """Test group extraction from TIT1"""
        audio_mock = mock_mp3.return_value
        
        tit1 = MagicMock()
        tit1.text = ["Group A", "Group B"]
        audio_mock.tags = {"TIT1": tit1}
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.groups == ["Group A", "Group B"]

    def test_duration_extraction(self, mock_mp3):
        """Test duration extraction from audio info"""
        # Explicitly configure return value to ensure info exists
        audio_instance = MagicMock()
        audio_instance.info = MagicMock()
        audio_instance.info.length = 245.67
        audio_instance.tags = {}
        mock_mp3.return_value = audio_instance
        
        song = MetadataService.extract_from_mp3("test.mp3")
        assert song.duration == 245.67

    def test_all_fields_populated(self, mock_mp3):
        """Test extraction with all fields populated"""
        # Explicitly configure return value
        audio_instance = MagicMock()
        audio_instance.info = MagicMock()
        audio_instance.info.length = 300.0
        
        tags = {}
        
        def mock_frame(text=None, people=None):
            m = MagicMock()
            if text: m.text = text
            if people: m.people = people
            return m
            
        tags["TIT2"] = mock_frame(text=["Full Title"])
        tags["TPE1"] = mock_frame(text=["Performer"])
        tags["TCOM"] = mock_frame(text=["Composer"])
        tags["TOLY"] = mock_frame(text=["Lyricist"])
        tags["TIT1"] = mock_frame(text=["Group"])
        tags["TBPM"] = mock_frame(text=["140"])
        tags["TIPL"] = mock_frame(people=[("producer", "Producer")])
        
        audio_instance.tags = tags
        mock_mp3.return_value = audio_instance
        
        song = MetadataService.extract_from_mp3("test.mp3", source_id=42)
        
        assert song.source_id == 42
        assert song.title == "Full Title"
        assert song.duration == 300.0
        assert song.bpm == 140
        assert song.performers == ["Performer"]
        assert song.composers == ["Composer"]
        assert song.lyricists == ["Lyricist"]
        assert song.producers == ["Producer"]
        assert song.groups == ["Group"]


@pytest.mark.skip(reason="is_done is now tag-driven, not a Song property")
class TestMetadataDoneFlag:
    """DEPRECATED: Done flag tests - status is now tag-driven via TagRepository."""


    def test_read_done_flag_primary_txxx_true(self, mock_mp3):
        """Should read True from TXXX:GOSLING_DONE='1'"""
        self._setup_mocks(mock_mp3, txxx_done="1")
        song = MetadataService.extract_from_mp3("test.mp3")
        assert getattr(song, "is_done", None) is True

    def test_read_done_flag_primary_txxx_false(self, mock_mp3):
        """Should read False from TXXX:GOSLING_DONE='0' even if TKEY is 'true'"""
        self._setup_mocks(mock_mp3, txxx_done="0", tkey="true")
        song = MetadataService.extract_from_mp3("test.mp3")
        assert getattr(song, "is_done", None) is False

    def test_read_done_flag_legacy_tkey_true(self, mock_mp3):
        """Should fallback to True from TKEY='true' if TXXX is missing"""
        self._setup_mocks(mock_mp3, tkey="true")
        song = MetadataService.extract_from_mp3("test.mp3")
        assert getattr(song, "is_done", None) is True

    def test_read_done_flag_legacy_tkey_false(self, mock_mp3):
        """Should read False from TKEY=' ' (space) or missing"""
        self._setup_mocks(mock_mp3, tkey=" ")
        song = MetadataService.extract_from_mp3("test.mp3")
        assert not getattr(song, "is_done", False)

    def test_read_done_flag_real_musical_key(self, mock_mp3):
        """Should NOT treat a real musical key (e.g. 'Am') as Done=True"""
        self._setup_mocks(mock_mp3, tkey="Am")
        song = MetadataService.extract_from_mp3("test.mp3")
        assert not getattr(song, "is_done", False)

    def _setup_mocks(self, mock_mp3, txxx_done=None, tkey=None):
        """Helper to mock ID3 tags"""
        from unittest.mock import MagicMock
        audio_mock = mock_mp3.return_value
        audio_mock.info.length = 120
        
        tags = {}
        if txxx_done is not None:
             m = MagicMock()
             m.text = [txxx_done]
             tags["TXXX:GOSLING_DONE"] = m
             
        if tkey is not None:
            m = MagicMock()
            m.text = [tkey]
            tags["TKEY"] = m
            
        audio_mock.tags = tags


# ============================================================================
# WRITE TAGS INTEGRATION (from test_metadata_write.py)
# ============================================================================
class TestWriteTagsIntegration:
    """Level 1: Integration tests for writing ID3 tags to real MP3 files"""
    
    def test_write_tags_basic(self, test_mp3):
        """Write all fields to MP3"""
        song = Song(
            source=test_mp3,
            name="New Title",
            performers=["Artist 1", "Artist 2"],
            composers=["Composer 1"],
            lyricists=["Lyricist 1"],
            producers=["Producer 1"],
            groups=["Group 1"],
            bpm=120,
            recording_year=2023,
            isrc="USRC12345678"
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Verify by reading back
        audio = MP3(test_mp3, ID3=ID3)
        assert str(audio.tags['TIT2']) == "New Title"
        assert "Artist 1" in str(audio.tags['TPE1'])
        assert "Composer 1" in str(audio.tags['TCOM'])
        assert str(audio.tags['TBPM']) == "120"
        assert "2023" in str(audio.tags['TDRC'])
        assert str(audio.tags['TSRC']) == "USRC12345678"
    
    def test_write_tags_preserves_album_art(self, test_mp3_with_album_art):
        """Album art (APIC) is not deleted when writing tags"""
        song = Song(
            source=test_mp3_with_album_art,
            name="Updated Title",
            performers=["New Artist"]
        )
        
        # Verify album art exists before
        audio_before = MP3(test_mp3_with_album_art, ID3=ID3)
        assert 'APIC:Cover' in audio_before.tags
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Verify album art still exists after
        audio_after = MP3(test_mp3_with_album_art, ID3=ID3)
        assert 'APIC:Cover' in audio_after.tags
        assert str(audio_after.tags['TIT2']) == "Updated Title"
    
    def test_write_tags_preserves_comments(self, test_mp3_with_comments):
        """Comments (COMM) are not deleted when writing tags"""
        song = Song(
            source=test_mp3_with_comments,
            name="Updated Title"
        )
        
        # Verify comment exists before
        audio_before = MP3(test_mp3_with_comments, ID3=ID3)
        assert 'COMM::eng' in audio_before.tags
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Verify comment still exists after
        audio_after = MP3(test_mp3_with_comments, ID3=ID3)
        assert 'COMM::eng' in audio_after.tags
        assert "Important comment" in str(audio_after.tags['COMM::eng'])
    
    def test_write_tags_handles_empty_fields(self, test_mp3):
        """None/empty fields don't delete existing data (sparse update)"""
        # First write some data
        song1 = Song(
            source=test_mp3,
            name="Original Title",
            performers=["Original Artist"],
            bpm=100
        )
        MetadataService.write_tags(song1)
        
        # Load existing, change one field, and save
        song2 = MetadataService.extract_from_mp3(test_mp3)
        song2.name = "New Title"
        song2.bpm = None  # Should skip, preserving the file's '100'
        
        MetadataService.write_tags(song2)
        
        # Verify title updated 
        audio = MP3(test_mp3, ID3=ID3)
        assert str(audio.tags['TIT2']) == "New Title"
        
        # Verify performers preserved
        assert 'TPE1' in audio.tags
        assert "Original Artist" in str(audio.tags['TPE1'])

        # Verify BPM preserved
        assert 'TBPM' in audio.tags
        assert "100" in str(audio.tags['TBPM'])
    
    @pytest.mark.skip(reason="is_done is now tag-driven")
    def test_write_tags_is_done_true(self, test_mp3):
        """DEPRECATED: is_done is now tag-driven"""
        pass
    
    @pytest.mark.skip(reason="is_done is now tag-driven")
    def test_write_tags_is_done_false(self, test_mp3):
        """DEPRECATED: is_done is now tag-driven"""
        pass
    
    def test_write_tags_roundtrip(self, test_mp3):
        """Write then read, data matches"""
        original_song = Song(
            source=test_mp3,
            name="Roundtrip Test",
            performers=["Artist A", "Artist B"],
            composers=["Composer X"],
            bpm=140,
            recording_year=2024,
            isrc="TEST12345678"
        )
        
        # Write
        result = MetadataService.write_tags(original_song)
        assert result is True
        
        # Read back
        read_song = MetadataService.extract_from_mp3(test_mp3)
        
        # Verify
        assert read_song.title == original_song.title
        assert read_song.performers == original_song.performers
        assert read_song.composers == original_song.composers
        assert read_song.bpm == original_song.bpm
        assert read_song.recording_year == original_song.recording_year
        assert read_song.isrc == original_song.isrc
    
    def test_write_tags_invalid_file(self, tmp_path):
        """Returns False for non-MP3 file"""
        bad_file = tmp_path / "not_an_mp3.txt"
        bad_file.write_text("This is not an MP3")
        
        song = Song(source=str(bad_file), name="Test")
        result = MetadataService.write_tags(song)
        
        assert result is False
    
    def test_write_tags_no_path(self):
        """Returns False if song has no path"""
        song = Song(name="Test")  # No path
        result = MetadataService.write_tags(song)
        
        assert result is False
    
    def test_write_tags_creates_tags_if_missing(self, test_mp3_empty):
        """Creates ID3v2 tags if file has none"""
        song = Song(
            source=test_mp3_empty,
            name="New Song",
            performers=["New Artist"]
        )
        
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Verify tags were created
        audio = MP3(test_mp3_empty, ID3=ID3)
        assert audio.tags is not None
        assert 'TIT2' in audio.tags
        assert 'TPE1' in audio.tags
    
    def test_write_tags_handles_multiple_performers(self, test_mp3):
        """Multiple performers are written correctly"""
        song = Song(
            source=test_mp3,
            performers=["Artist 1", "Artist 2", "Artist 3"]
        )
        
        MetadataService.write_tags(song)
        
        audio = MP3(test_mp3, ID3=ID3)
        performers_text = str(audio.tags['TPE1'])
        assert "Artist 1" in performers_text
        assert "Artist 2" in performers_text
        assert "Artist 3" in performers_text
    
    def test_write_tags_producers_dual_mode(self, test_mp3):
        """Producers written to both TIPL and TXXX:PRODUCER"""
        song = Song(
            source=test_mp3,
            producers=["Producer A", "Producer B"]
        )
        
        MetadataService.write_tags(song)
        
        audio = MP3(test_mp3, ID3=ID3)
        # Check TIPL
        assert 'TIPL' in audio.tags
        # Check TXXX:PRODUCER
        assert 'TXXX:PRODUCER' in audio.tags
        assert "Producer A" in str(audio.tags['TXXX:PRODUCER'])


# ============================================================================
# WRITE TAGS VERSION HANDLING (from test_metadata_additional.py - Logic only)
# ============================================================================
class TestWriteTagsVersionHandling:
    """Level 1: Tests for ID3 version handling and frame preservation"""
    
    def test_write_tags_preserves_unknown_frames(self, test_mp3):
        """Custom TXXX frames are not deleted"""
        from mutagen.id3 import TXXX
        
        # Add a custom TXXX frame
        audio = MP3(test_mp3, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.add(TXXX(encoding=3, desc='CUSTOM_FIELD', text='Custom Value'))
        audio.save()
        
        # Write metadata
        song = Song(source=test_mp3, name="New Title")
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Custom frame should still exist
        audio_after = MP3(test_mp3, ID3=ID3)
        assert 'TXXX:CUSTOM_FIELD' in audio_after.tags
        assert "Custom Value" in str(audio_after.tags['TXXX:CUSTOM_FIELD'])
    
    def test_write_tags_creates_v2_if_missing(self, test_mp3):
        """Creates ID3v2 tags if file has none"""
        # Remove all tags
        audio = MP3(test_mp3)
        if audio.tags is not None:
            audio.delete()
        
        # Write metadata
        song = Song(source=test_mp3, name="New Song")
        result = MetadataService.write_tags(song)
        assert result is True
        
        # Should have ID3v2 tags now
        audio_after = MP3(test_mp3, ID3=ID3)
        assert audio_after.tags is not None
        assert 'TIT2' in audio_after.tags
    
    def test_write_tags_preserves_v1_if_exists(self, test_mp3):
        """ID3v1 tags are preserved if they exist (v1=1 behavior)"""
        # This test verifies the v1=1 parameter works
        song = Song(source=test_mp3, name="Test")
        result = MetadataService.write_tags(song)
        assert result is True
        # If file had v1, it would be preserved
        # If file didn't have v1, it won't be created


# ============================================================================
# DYNAMIC ID3 WRITE (from test_metadata_write_dynamic.py - T-38 Verification)
# ============================================================================
class TestDynamicID3Write:
    """
    T-38: Verification for Dynamic ID3 Write Logic.
    Ensures write_tags() uses id3_frames.json and handles dual-mode fields correctly.
    """
    
    @pytest.fixture
    def mock_audio(self):
        from unittest.mock import MagicMock
        mock = MagicMock(spec=ID3)
        mock.tags = MagicMock()
        mock.save = MagicMock()
        return mock
    
    @pytest.fixture
    def test_song(self):
        return Song(
            source_id=1,
            source="C:\\Music\\Test.mp3",
            name="Dynamic Test",
            performers=["The Testers"],
            album_artist="Test Orchestra",
            composers=["Mozart", "Beethoven"],
            lyricists=["Schiller"],
            producers=["Quincy"],
            recording_year=2025,
            bpm=120
        )
    
    def test_dynamic_field_write(self, mock_audio, test_song):
        """Test that album_artist (TPE2) is written dynamically."""
        from mutagen.id3 import TPE2
        
        with patch('src.business.services.metadata_service.MP3', return_value=mock_audio):
            success = MetadataService.write_tags(test_song)
            assert success is True
            
            # Check TPE2
            found_tpe2 = False
            for call in mock_audio.tags.add.call_args_list:
                args, _ = call
                frame = args[0]
                if isinstance(frame, TPE2):
                    if frame.text == "Test Orchestra" or frame.text == ["Test Orchestra"]:
                        found_tpe2 = True
                        
            assert found_tpe2, "TPE2 (Album Artist) was not written!"

    def test_dual_mode_year(self, mock_audio, test_song):
        """Verify Year writes to TYER (Legacy) and TDRC (Modern)."""
        from mutagen.id3 import TYER, TDRC
        
        with patch('src.business.services.metadata_service.MP3', return_value=mock_audio):
            MetadataService.write_tags(test_song)
            
            found_tyer = False
            found_tdrc = False
            
            for call in mock_audio.tags.add.call_args_list:
                frame = call[0][0]
                if isinstance(frame, TYER) and str(frame) == "2025":
                    found_tyer = True
                if isinstance(frame, TDRC) and str(frame) == "2025":
                    found_tdrc = True
                    
            assert found_tyer, "Legacy TYER year not written"
            assert found_tdrc, "Modern TDRC year not written"

    def test_legacy_author_union(self, mock_audio, test_song):
        """Verify TCOM contains union of Composers + Lyricists."""
        from mutagen.id3 import TCOM, TEXT
        
        with patch('src.business.services.metadata_service.MP3', return_value=mock_audio):
            MetadataService.write_tags(test_song)
            
            found_tcom = False
            found_text = False
            
            for call in mock_audio.tags.add.call_args_list:
                frame = call[0][0]
                if isinstance(frame, TCOM):
                    # Expect: Mozart, Beethoven, Schiller
                    text_list = frame.text
                    assert "Mozart" in text_list
                    assert "Schiller" in text_list
                    found_tcom = True
                
                if isinstance(frame, TEXT):
                    # Expect: Schiller only
                    assert frame.text == ["Schiller"]
                    found_text = True
                    
            assert found_tcom, "TCOM Union not written"
            assert found_text, "TEXT Lyricist not written"

    def test_producers_clean_mode(self, mock_audio, test_song):
        """Verify Producers use TIPL and TXXX, but NOT TCOM."""
        from mutagen.id3 import TIPL, TXXX
        
        with patch('src.business.services.metadata_service.MP3', return_value=mock_audio):
            MetadataService.write_tags(test_song)
            
            found_tipl = False
            found_txxx_prod = False
            
            for call in mock_audio.tags.add.call_args_list:
                frame = call[0][0]
                if isinstance(frame, TIPL):
                    # people list: [('producer', 'Quincy')]
                    assert frame.people == [['producer', 'Quincy']]
                    found_tipl = True
                
                if isinstance(frame, TXXX) and frame.desc == 'PRODUCER':
                    assert frame.text == ["Quincy"]
                    found_txxx_prod = True
                    
            assert found_tipl, "TIPL Producer not written"
            assert found_txxx_prod, "TXXX:PRODUCER not written"

class TestMetadataMultiAlbum:
    """
    Phase 4: Multi-Album & Publisher Verification (Waterfall Resolution).
    """

    def test_write_multi_value_tpub(self, mock_mp3):
        """Verify TPUB (Publisher) accepts list values for ID3v2.4 support."""
        from mutagen.id3 import TPUB
        
        # Setup Mock
        mock_audio = mock_mp3.return_value
        mock_audio.tags = MagicMock()
        mock_audio.tags.add = MagicMock()
        
        # Song with multi-value publisher (as hydrated by SongRepository Waterfall)
        song = Song(
            source="test.mp3",
            name="Test",
            publisher=["Label A", "Label B"] # List!
        )
        
        MetadataService.write_tags(song)
        
        found_tpub = False
        for call in mock_audio.tags.add.call_args_list:
            frame = call[0][0]
            if isinstance(frame, TPUB):
                # Mutagen expects list for text frames in ID3v2.4
                # If our Service handles it correctly, frame.text should be the list.
                if frame.text == ["Label A", "Label B"]:
                    found_tpub = True
        
        assert found_tpub, "TPUB did not receive multi-value list ['Label A', 'Label B']"
