
import pytest
from src.services.catalog_service import CatalogService

class TestCatalogCasing:
    def test_format_song_media_name_sentence_case(self, populated_db):
        service = CatalogService(populated_db)
        song_id = 1  # "Smells Like Teen Spirit"
        
        # ACT
        new_value = service.format_entity_field("song", song_id, "media_name", "sentence")
        
        # ASSERT
        assert new_value == "Smells like teen spirit", f"Expected 'Smells like teen spirit', got '{new_value}'"
        
        # Verify persistence
        song = service.get_song(song_id)
        assert song.media_name == "Smells like teen spirit"

    def test_format_song_media_name_title_case(self, populated_db):
        service = CatalogService(populated_db)
        song_id = 1
        # First set it to lowercase to ensure transformation happens
        service.update_song_scalars(song_id, {"media_name": "smells like teen spirit"})
        
        # ACT
        new_value = service.format_entity_field("song", song_id, "media_name", "title")
        
        # ASSERT
        assert new_value == "Smells Like Teen Spirit", f"Expected 'Smells Like Teen Spirit', got '{new_value}'"
        
        # Verify persistence
        song = service.get_song(song_id)
        assert song.media_name == "Smells Like Teen Spirit"

    def test_format_album_title_sentence_case(self, populated_db):
        service = CatalogService(populated_db)
        album_id = 100  # "Nevermind"
        # Set to uppercase
        service.update_album(album_id, {"title": "NEVERMIND"})
        
        # ACT
        new_value = service.format_entity_field("album", album_id, "title", "sentence")
        
        # ASSERT
        assert new_value == "Nevermind"
        
        # Verify persistence
        album = service.get_album(album_id)
        assert album.title == "Nevermind"

    def test_format_publisher_name_title_case(self, populated_db):
        service = CatalogService(populated_db)
        pub_id = 5  # "Sub Pop"
        # Set to lowercase
        service.update_publisher(pub_id, "sub pop")
        
        # ACT
        new_value = service.format_entity_field("publisher", pub_id, "name", "title")
        
        # ASSERT
        assert new_value == "Sub Pop"

