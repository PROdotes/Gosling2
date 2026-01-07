"""Unit tests for Identity model"""
import pytest
from src.data.models.identity import Identity


class TestIdentityModel:
    """Test cases for Identity model"""

    def test_identity_creation_with_defaults(self):
        """Test creating an identity with default values"""
        identity = Identity()

        assert identity.identity_id is None
        assert identity.identity_type == "person"
        assert identity.legal_name is None
        assert identity.biography is None

    def test_identity_creation_with_values(self):
        """Test creating an identity with specific values"""
        identity = Identity(
            identity_id=1,
            identity_type="group",
            legal_name="The Beatles",
            formation_date="1960-01-01",
            biography="English rock band formed in Liverpool in 1960."
        )

        assert identity.identity_id == 1
        assert identity.identity_type == "group"
        assert identity.legal_name == "The Beatles"
        assert identity.formation_date == "1960-01-01"
        assert identity.biography == "English rock band formed in Liverpool in 1960."

    def test_to_dict(self):
        """Test converting identity to dictionary"""
        identity = Identity(
            identity_id=1,
            identity_type="person",
            legal_name="David Bowie"
        )
        data = identity.to_dict()
        assert data["identity_id"] == 1
        assert data["identity_type"] == "person"
        assert data["legal_name"] == "David Bowie"
