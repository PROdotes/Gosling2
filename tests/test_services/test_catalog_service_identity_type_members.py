"""
Service-layer tests for identity type conversion and group membership.
These are passthroughs — one happy path + surface-level error mapping per method.
Edge cases and guards are covered by the repo tests.

populated_db fixtures:
  ID=1: person  "Dave Grohl"    aliases: Grohlton(11), Late!(12), Ines Prajo(33)
  ID=2: group   "Nirvana"       members: Dave(1)
  ID=3: group   "Foo Fighters"  members: Dave(1), Taylor(4)
  ID=4: person  "Taylor Hawkins"
"""

import pytest


class TestSetIdentityType:
    def test_happy_path(self, catalog_service):
        catalog_service.set_identity_type(4, "group")
        assert catalog_service.get_identity(4).type == "group"

    def test_not_found_raises(self, catalog_service):
        with pytest.raises(LookupError):
            catalog_service.set_identity_type(9999, "group")

    def test_blocked_raises(self, catalog_service):
        with pytest.raises(ValueError):
            catalog_service.set_identity_type(2, "person")  # Nirvana has members


class TestAddIdentityMember:
    def test_happy_path(self, catalog_service):
        catalog_service.add_identity_member(2, 4)
        member_ids = {m.id for m in catalog_service.get_identity(2).members}
        assert 4 in member_ids

    def test_not_found_raises(self, catalog_service):
        with pytest.raises(LookupError):
            catalog_service.add_identity_member(9999, 1)

    def test_guard_raises(self, catalog_service):
        with pytest.raises(ValueError):
            catalog_service.add_identity_member(2, 2)  # self-membership


class TestRemoveIdentityMember:
    def test_happy_path(self, catalog_service):
        catalog_service.remove_identity_member(2, 1)
        member_ids = {m.id for m in catalog_service.get_identity(2).members}
        assert 1 not in member_ids

    def test_noop_if_not_linked(self, catalog_service):
        catalog_service.remove_identity_member(
            2, 4
        )  # Taylor not in Nirvana — should not raise
