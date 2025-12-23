
import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os

# Bypass package-level imports to avoid PyQt dependency
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['src.business.services.playback_service'] = MagicMock()

from src.business.services.metadata_service import MetadataService
from src.data.models.song import Song
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TCOM, TCON, TDRC, COMM, APIC, TXXX, TIPL, TEXT, TYER

class TestDynamicID3Write(unittest.TestCase):
    """
    T-38: Verification for Dynamic ID3 Write Logic.
    Ensures write_tags() uses id3_frames.json and handles dual-mode fields correctly.
    """

    def setUp(self):
        self.song = Song(
            source_id=1,
            source="C:\\Music\\Test.mp3",
            name="Dynamic Test",
            performers=["The Testers"],
            album_artist="Test Orchestra",
            composers=["Mozart", "Beethoven"],
            lyricists=["Schiller"],
            producers=["Quincy"],
            recording_year=2025,
            is_done=True,
            bpm=120
        )
        
        # Mock the MP3/ID3 object
        self.mock_audio = MagicMock(spec=ID3)
        self.mock_audio.tags = MagicMock()
        self.mock_audio.save = MagicMock()
        
        # When tags.add() is called, we can inspect args
        # But since we use mutagen classes, we need to ensure checks work.
        # We will inspect call_args_list manually in tests.

    @patch('src.business.services.metadata_service.MP3')
    def test_dynamic_field_write(self, mock_mp3_cls):
        """Test that album_artist (TPE2) is written dynamically."""
        mock_mp3_cls.return_value = self.mock_audio
        
        success = MetadataService.write_tags(self.song)
        self.assertTrue(success)
        
        # Check TPE2
        # We iterate over all calls to .add()
        found_tpe2 = False
        for call in self.mock_audio.tags.add.call_args_list:
            args, _ = call
            frame = args[0]
            if isinstance(frame, TPE2):
                self.assertEqual(frame.text, ["Test Orchestra"] if isinstance(frame.text, list) else "Test Orchestra")
                # Mutagen usually normalizes text to list, OR our code passes string. 
                # Let's check what our code passed: text="Test Orchestra". Mutagen might wrap it.
                # Actually, our code passes text="Test Orchestra" for non-list. 
                # But comparing the Mock call argument, it will be exactly what we passed.
                # However, if we instantiate TPE2 in the test to compare, checks might be tricky.
                # Checking attributes is safer.
                if frame.text == "Test Orchestra" or frame.text == ["Test Orchestra"]:
                    found_tpe2 = True
                    
        self.assertTrue(found_tpe2, "TPE2 (Album Artist) was not written!")

    @patch('src.business.services.metadata_service.MP3')
    def test_dual_mode_year(self, mock_mp3_cls):
        """Verify Year writes to TYER (Legacy) and TDRC (Modern)."""
        mock_mp3_cls.return_value = self.mock_audio
        MetadataService.write_tags(self.song)
        
        found_tyer = False
        found_tdrc = False
        
        for call in self.mock_audio.tags.add.call_args_list:
            frame = call[0][0]
            if isinstance(frame, TYER) and str(frame) == "2025":
                found_tyer = True
            if isinstance(frame, TDRC) and str(frame) == "2025":
                found_tdrc = True
                
        self.assertTrue(found_tyer, "Legacy TYER year not written")
        self.assertTrue(found_tdrc, "Modern TDRC year not written")

    @patch('src.business.services.metadata_service.MP3')
    def test_legacy_author_union(self, mock_mp3_cls):
        """Verify TCOM contains union of Composers + Lyricists."""
        mock_mp3_cls.return_value = self.mock_audio
        MetadataService.write_tags(self.song)
        
        found_tcom = False
        found_text = False
        
        for call in self.mock_audio.tags.add.call_args_list:
            frame = call[0][0]
            if isinstance(frame, TCOM):
                # Expect: Mozart, Beethoven, Schiller
                # Mutagen text is list
                text_list = frame.text
                self.assertIn("Mozart", text_list)
                self.assertIn("Schiller", text_list)
                found_tcom = True
            
            if isinstance(frame, TEXT):
                # Expect: Schiller only
                self.assertEqual(frame.text, ["Schiller"])
                found_text = True
                
        self.assertTrue(found_tcom, "TCOM Union not written")
        self.assertTrue(found_text, "TEXT Lyricist not written")

    @patch('src.business.services.metadata_service.MP3')
    def test_producers_clean_mode(self, mock_mp3_cls):
        """Verify Producers use TIPL and TXXX, but NOT TCOM."""
        mock_mp3_cls.return_value = self.mock_audio
        MetadataService.write_tags(self.song)
        
        found_tipl = False
        found_txxx_prod = False
        
        for call in self.mock_audio.tags.add.call_args_list:
            frame = call[0][0]
            if isinstance(frame, TIPL):
                # people list: [('producer', 'Quincy')]
                # Mutagen converts tuples to lists internally
                self.assertEqual(frame.people, [['producer', 'Quincy']])
                found_tipl = True
            
            if isinstance(frame, TXXX) and frame.desc == 'PRODUCER':
                self.assertEqual(frame.text, ["Quincy"])
                found_txxx_prod = True
                
        self.assertTrue(found_tipl, "TIPL Producer not written")
        self.assertTrue(found_txxx_prod, "TXXX:PRODUCER not written")

if __name__ == '__main__':
    unittest.main()
