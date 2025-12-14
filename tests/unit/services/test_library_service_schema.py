import pytest
from unittest.mock import MagicMock
from src.business.services.library_service import LibraryService

def test_get_all_songs_schema_pass_through():
    """
    Service Schema Integrity Test:
    Ensures LibraryService.get_all_songs() faithfully returns the 
    data structure provided by SongRepository.
    
    If the repository schema changes (which is caught by test_song_repository_schema.py),
    this test ensures the Service layer doesn't silently swallow or transform it unexpectedly.
    """
    service = LibraryService()
    service.song_repository = MagicMock()
    
    # Simulate Repository output
    expected_headers = ["FileID", "Performers", "Title", "Duration", "Path", "Composers", "BPM"]
    expected_data = [(1, "P", "T", 100, "/path", "C", 120)]
    
    service.song_repository.get_all.return_value = (expected_headers, expected_data)
    
    # Call Service
    headers, data = service.get_all_songs()
    
    # Verify strict pass-through
    assert headers == expected_headers, \
        f"Service layer modified headers! Expected {expected_headers}, got {headers}"
    
    assert data == expected_data, \
        f"Service layer modified data! Expected {expected_data}, got {data}"
        
def test_get_all_songs_schema_change_detection():
    """
    Simulate a Schema Change from Repository and ensure Service propagates it.
    If we add 'Genre' to Repository, Service typically should pass it through.
    """
    service = LibraryService()
    service.song_repository = MagicMock()
    
    # Simulate NEW Schema
    new_headers = ["FileID", "Performers", "Title", "Duration", "Path", "Composers", "BPM", "Genre"]
    new_data = [(1, "P", "T", 100, "/path", "C", 120, "Rock")]
    
    service.song_repository.get_all.return_value = (new_headers, new_data)
    
    headers, data = service.get_all_songs()
    
    assert headers == new_headers
    assert len(data[0]) == 8 # 8 columns
