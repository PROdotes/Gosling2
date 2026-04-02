"""
Unit tests for Spotify Pydantic models.
Verifies that models support elective identity resolution for Truth-First linking.
"""

from src.engine.models.spotify import SpotifyCredit, SpotifyImportRequest


def test_spotify_credit_model_supports_optional_identity():
    """SpotifyCredit must accept an optional identity_id for manual resolution."""
    # CASE A: Standard import (no identity resolved yet)
    credit_raw = SpotifyCredit(name="Andres Kõpper", role="Performer")
    assert credit_raw.name == "Andres Kõpper"
    assert credit_raw.role == "Performer"
    assert getattr(credit_raw, "identity_id", None) is None

    # CASE B: Resolved import (mapped to NOËP in UI)
    credit_resolved = SpotifyCredit(
        name="Andres Kõpper", role="Performer", identity_id=234
    )
    assert credit_resolved.identity_id == 234


def test_spotify_import_request_serialization():
    """SpotifyImportRequest must handle the transit of resolved identity IDs."""
    data = {
        "song_id": 1,
        "credits": [
            {"name": "Andres Kõpper", "role": "Performer", "identity_id": 234},
            {"name": "Goran Boskovic", "role": "Composer"},
        ],
        "publishers": ["Menart"],
    }

    req = SpotifyImportRequest(**data)
    assert req.song_id == 1
    assert req.credits[0].identity_id == 234
    assert req.credits[1].identity_id is None
