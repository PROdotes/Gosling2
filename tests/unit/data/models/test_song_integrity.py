import pytest
import dataclasses
from src.data.models.song import Song

def test_song_model_schema_stability():
    """
    Model Integrity Test:
    Ensures that the Song data model has exactly the expected fields.
    If a developer adds 'genre' to the Song class, this test will fail,
    forcing them to explicitly update this test (and hopefully recall to check DB/Repo).
    """
    expected_fields = {
        "file_id",
        "path",
        "title",
        "duration",
        "bpm",
        "performers",
        "composers",
        "lyricists",
        "producers",
        "groups"
    }
    
    actual_fields = {f.name for f in dataclasses.fields(Song)}
    
    missing = expected_fields - actual_fields
    extra = actual_fields - expected_fields
    
    assert not missing, f"Song Model missing expected fields: {missing}"
    assert not extra, f"Song Model has unexpected extra fields: {extra}. Update this test AND DB schema tests."
