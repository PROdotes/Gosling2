"""Unit tests for Role model"""
import pytest
from src.data.models.role import Role, RoleType


class TestRoleModel:
    """Test cases for Role model"""

    def test_role_creation_with_defaults(self):
        """Test creating a role with default values"""
        role = Role()

        assert role.role_id is None
        assert role.name == ""

    def test_role_creation_with_values(self):
        """Test creating a role with specific values"""
        role = Role(role_id=1, name="Performer")

        assert role.role_id == 1
        assert role.name == "Performer"

    def test_role_type_enum(self):
        """Test RoleType enum values"""
        assert RoleType.PERFORMER.value == "Performer"
        assert RoleType.COMPOSER.value == "Composer"
        assert RoleType.LYRICIST.value == "Lyricist"
        assert RoleType.PRODUCER.value == "Producer"

