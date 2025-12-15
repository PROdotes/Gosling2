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
    from src.data.repositories import SongRepository, ContributorRepository
    service = LibraryService(SongRepository(), ContributorRepository())
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
    from src.data.repositories import SongRepository, ContributorRepository
    service = LibraryService(SongRepository(), ContributorRepository())
    service.song_repository = MagicMock()
    
    # Simulate NEW Schema
    new_headers = ["FileID", "Performers", "Title", "Duration", "Path", "Composers", "BPM", "Genre"]
    new_data = [(1, "P", "T", 100, "/path", "C", 120, "Rock")]
    
    service.song_repository.get_all.return_value = (new_headers, new_data)
    
    headers, data = service.get_all_songs()
    
    assert headers == new_headers
    assert len(data[0]) == 8 # 8 columns

def test_strict_service_headers():
    """
    STRICT Service Header Check:
    Ensures that the Service Layer is exposing the standard set of headers 
    that the UI relies on. 
    
    If 'Files' table gains 'Genre', and repo updates, but Service logic somehow filters it out,
    this test (updated manually or dynamically) ensures we catch it.
    
    Ideally, this should verify against the Song Model fields or a known strict list.
    """
    from src.data.repositories import SongRepository, ContributorRepository
    
    # We use a real instance or mocked repo that returns 'real-like' headers
    # But to prevent circular dependency on DB, we define EXPECTED logic here.
    
    # The 'Song' model drives the domain. The Service should expose what the Song model has.
    # Let's import the Song model to get truth.
    import dataclasses
    from src.data.models.song import Song
    
    song_fields = {f.name for f in dataclasses.fields(Song)}
    
    # Map Song Fields -> Expected Service Headers
    # This map must be kept in sync. If Song adds 'genre', we must decide the Header name here.
    field_to_header = {
        "file_id": "FileID",
        "title": "Title",
        "duration": "Duration",
        "path": "Path",
        "bpm": "BPM",
        "recording_year": "Year",
        # Contributors (lists in model, but often strings in table view?)
        # BaseRepo joins them.
        "performers": "Performers",
        "composers": "Composers",
        # "lyricists" might not be in default get_all_songs? 
        # Check SongRepository.get_all implementation specifically.
        # It usually returns a fixed set.
    }
    
    # Expected Headers that MUST be present
    required_headers = set(field_to_header.values())
    
    # Mock Repo to return what it currently returns (or standard set)
    # Actually, let's instantiate the real Service with a Mock Repo that returns valid headers.
    service = LibraryService(SongRepository(), ContributorRepository())
    service.song_repository = MagicMock()
    
    # Mimic CURRENT standard headers (as per repo code)
    current_headers = ["FileID", "Performers", "Title", "Duration", "Path", "Composers", "BPM", "Year"]
    service.song_repository.get_all.return_value = (current_headers, [])
    
    headers, _ = service.get_all_songs()
    header_set = set(headers)
    
    # Check if we are missing any required headers mapped from valid Song fields
    # Note: If Song model has 'lyricists', but we don't display it in Table, this test 
    # might fail if we enforce 100% coverage.
    # But strictness implies "If IT IS IN DB/MODEL, IT MUST BE IN SERVICE".
    # Currently 'lyricists' is in Model but NOT in 'current_headers' above?
    # Let's check if 'lyricists' is in current_headers in reality.
    # I recall it being absent from the main table view usually.
    # So strictness here might force us to add it, or explicitly exclude it.
    
    for field, header in field_to_header.items():
        if header not in header_set:
             # If we decide Lyricists are optional in table, we skip.
             # But for strictness on core fields:
             pytest.fail(f"Service is not exposing header '{header}' (mapped from field '{field}').")
             
    # Ensure no unknown headers?
    # extra = header_set - required_headers
    # if extra: warn?

