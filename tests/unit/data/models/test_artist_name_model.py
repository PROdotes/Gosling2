"""Unit tests for ArtistName model"""
import pytest
from src.data.models.artist_name import ArtistName


class TestArtistNameModel:
    """Test cases for ArtistName model"""

    def test_artist_name_creation_with_defaults(self):
        """Test creating an artist name with default values"""
        name = ArtistName(display_name="Ziggy Stardust")

        assert name.name_id is None
        assert name.owner_identity_id is None
        assert name.display_name == "Ziggy Stardust"
        assert name.sort_name == "Ziggy Stardust"
        assert name.is_primary_name is False

    def test_artist_name_creation_with_values(self):
        """Test creating an artist name with specific values"""
        name = ArtistName(
            name_id=10,
            owner_identity_id=1,
            display_name="David Bowie",
            sort_name="Bowie, David",
            is_primary_name=True,
            disambiguation_note="Legend"
        )

        assert name.name_id == 10
        assert name.owner_identity_id == 1
        assert name.display_name == "David Bowie"
        assert name.sort_name == "Bowie, David"
        assert name.is_primary_name is True
        assert name.disambiguation_note == "Legend"

    def test_post_init_sets_sort_name(self):
        """Test that post_init sets sort_name from display_name if not provided"""
        name = ArtistName(display_name="Prince")
        assert name.sort_name == "Prince"

    def test_to_dict(self):
        """Test converting artist name to dictionary"""
        name = ArtistName(
            name_id=10,
            display_name="David Bowie",
            is_primary_name=True
        )
        data = name.to_dict()
        assert data["name_id"] == 10
        assert data["display_name"] == "David Bowie"
        assert data["is_primary_name"] is True
