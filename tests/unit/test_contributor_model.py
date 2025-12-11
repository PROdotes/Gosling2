"""Unit tests for Contributor model"""
import pytest
from src.data.models.contributor import Contributor


class TestContributorModel:
    """Test cases for Contributor model"""

    def test_contributor_creation_with_defaults(self):
        """Test creating a contributor with default values"""
        contributor = Contributor()

        assert contributor.contributor_id is None
        assert contributor.name == ""
        assert contributor.sort_name == ""

    def test_contributor_creation_with_values(self):
        """Test creating a contributor with specific values"""
        contributor = Contributor(
            contributor_id=1,
            name="John Doe",
            sort_name="Doe, John"
        )

        assert contributor.contributor_id == 1
        assert contributor.name == "John Doe"
        assert contributor.sort_name == "Doe, John"

    def test_post_init_sets_sort_name(self):
        """Test that post_init sets sort_name from name if not provided"""
        contributor = Contributor(name="Jane Smith")
        assert contributor.sort_name == "Jane Smith"

    def test_post_init_preserves_explicit_sort_name(self):
        """Test that explicit sort_name is preserved"""
        contributor = Contributor(name="Jane Smith", sort_name="Smith, Jane")
        assert contributor.sort_name == "Smith, Jane"

