import unittest
from src.data.models.album import Album

class TestAlbumModel(unittest.TestCase):
    """Unit tests for Album dataclass"""

    def test_init(self):
        """Test basic initialization"""
        album = Album(title="Test Album", album_type="EP", release_year=2023)
        self.assertEqual(album.title, "Test Album")
        self.assertEqual(album.album_type, "EP")
        self.assertEqual(album.release_year, 2023)
        self.assertEqual(album.tracks, [])

    def test_from_row_valid(self):
        """Test from_row with a valid tuple (New Schema: No AlbumArtist)"""
        # Row: (AlbumID, Title, AlbumType, ReleaseYear)
        row = (1, "Row Album", "Single", 1999)
        album = Album.from_row(row)
        
        self.assertEqual(album.album_id, 1)
        self.assertEqual(album.title, "Row Album")
        self.assertEqual(album.album_type, "Single")
        self.assertEqual(album.release_year, 1999)
        # AlbumArtist is computed via M2M, so it's None in the bare model from row
        self.assertIsNone(album.album_artist)

    def test_from_row_none_values(self):
        """Test from_row with None values where allowed"""
        row = (None, "Untitled", None, None)
        album = Album.from_row(row)
        
        self.assertIsNone(album.album_id)
        self.assertEqual(album.title, "Untitled")
        self.assertIsNone(album.album_type)
        self.assertIsNone(album.release_year)
        self.assertIsNone(album.album_artist)

if __name__ == "__main__":
    unittest.main()
