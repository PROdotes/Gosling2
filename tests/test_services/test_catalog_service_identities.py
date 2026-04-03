import pytest


class TestCatalogServiceIdentities:
    """CatalogService Identity and Alias mutation contracts."""

    def test_resolve_identity_by_name_success(self, catalog_service):
        """Truth-First: Should return IdentityID for an existing ArtistName."""
        # 'Dave Grohl' is NameID 1, linked to Identity ID 1 in populated_db.
        identity_id = catalog_service.resolve_identity_by_name("Dave Grohl")
        assert identity_id == 1, f"Expected identity 1, got {identity_id}"

    def test_resolve_identity_by_name_not_found_returns_none(self, catalog_service):
        identity_id = catalog_service.resolve_identity_by_name("Unknown Person")
        assert identity_id is None

    def test_add_identity_alias_success(self, catalog_service):
        """Link a new name to Dave Grohl (ID 1)."""
        name_id = catalog_service.add_identity_alias(1, "New Grohl Alias")
        assert name_id > 0

        # Verify resolution
        assert catalog_service.resolve_identity_by_name("New Grohl Alias") == 1

    def test_add_identity_alias_idempotent(self, catalog_service):
        """Adding same alias twice returns same ID."""
        id1 = catalog_service.add_identity_alias(1, "Foo")
        id2 = catalog_service.add_identity_alias(1, "Foo")
        assert id1 == id2

    def test_add_identity_alias_invalid_id_raises(self, catalog_service):
        with pytest.raises(LookupError, match="not found"):
            catalog_service.add_identity_alias(999, "Error")


class TestAddIdentityAliasReassignment:
    """Truth-First: Re-linking aliases between identities."""

    def test_relink_alias_from_other_identity(self, catalog_service):
        """Move non-primary alias 'Late!' (ID=12) from identity 1 to Identity 2."""
        # Scenario: "Late!" is a child of Dave. Safe to relink.
        catalog_service.add_identity_alias(2, "Late!", name_id=12)

        # Verify ID 1 survives but lost the alias
        id1 = catalog_service.get_identity(1)
        assert not any(a.display_name == "Late!" for a in id1.aliases)
        assert any(
            a.display_name == "Dave Grohl" for a in id1.aliases
        ), "Parent must survive"

    def test_relink_primary_name_parent_raises(self, catalog_service):
        """
        Move 'Dave Grohl' (Primary, ID=10) to ID 2.
        Dave has other aliases ('Grohlton', 'Late!'), so he is a Parent.
        Theft of the primary is UNSAFE (409 Conflict).
        """
        with pytest.raises(ValueError, match="already has other aliases"):
            catalog_service.add_identity_alias(2, "Dave Grohl", name_id=10)

    def test_relink_primary_name_solo_identity_succeeds(self, catalog_service):
        """
        Create a solo identity 'Solo Artist'. Move it to Identity 1.
        Safe: It has no other children to orphan.
        """
        repo = catalog_service._identity_repo
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Identities (IdentityType) VALUES ('person')")
            solo_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO ArtistNames (OwnerIdentityID, DisplayName, IsPrimaryName) VALUES (?, ?, 1)",
                (solo_id, "Solo Artist"),
            )
            solo_name_id = cursor.lastrowid
            conn.commit()

        # Act: Move the solo primary to ID 1
        catalog_service.add_identity_alias(1, "Solo Artist", name_id=solo_name_id)

        # Assert: ID 1 gained it, solo_id was merged
        id1 = catalog_service.get_identity(1)
        assert any(a.display_name == "Solo Artist" for a in id1.aliases)
        assert catalog_service.get_identity(solo_id) is None


class TestRemoveIdentityAlias:
    def test_remove_alias_removes_it(self, catalog_service):
        """Remove non-primary alias Grohlton (NameID=11) from identity 1."""
        catalog_service.remove_identity_alias(11)
        identity = catalog_service.get_identity(1)
        alias_names = [a.display_name for a in identity.aliases]
        assert (
            "Grohlton" not in alias_names
        ), f"Expected 'Grohlton' removed, got {alias_names}"

    def test_remove_alias_leaves_other_aliases(self, catalog_service):
        """Removing NameID=11 should not affect NameID=12 (Late!)."""
        catalog_service.remove_identity_alias(11)
        identity = catalog_service.get_identity(1)
        alias_names = [a.display_name for a in identity.aliases]
        assert "Late!" in alias_names, f"Expected 'Late!' to remain, got {alias_names}"

    def test_remove_primary_name_raises(self, catalog_service):
        """Cannot remove primary name (NameID=10, Dave Grohl)."""
        with pytest.raises(ValueError):
            catalog_service.remove_identity_alias(10)
        identity = catalog_service.get_identity(1)
        alias_names = [a.display_name for a in identity.aliases]
        assert (
            "Dave Grohl" in alias_names
        ), "Expected 'Dave Grohl' to remain after failed remove"

    def test_remove_nonexistent_name_is_noop(self, catalog_service):
        """Removing a name_id that doesn't exist should not raise."""
        catalog_service.remove_identity_alias(999)  # should not raise


# ---------------------------------------------------------------------------
# update_identity_legal_name
# ---------------------------------------------------------------------------

class TestUpdateIdentityLegalName:

    def test_update_legal_name_success(self, catalog_service):
        """Valid update persists and is returned by get_identity."""
        catalog_service.update_identity_legal_name(1, "David Eric Grohl Jr.")
        identity = catalog_service.get_identity(1)
        assert identity.legal_name == "David Eric Grohl Jr.", f"Expected updated name, got {identity.legal_name}"

    def test_update_legal_name_clear_to_none(self, catalog_service):
        """Setting to None clears the legal name."""
        catalog_service.update_identity_legal_name(1, None)
        identity = catalog_service.get_identity(1)
        assert identity.legal_name is None, f"Expected None, got {identity.legal_name}"

    def test_update_legal_name_invalid_id_raises(self, catalog_service):
        """Non-existent identity_id should raise LookupError."""
        with pytest.raises(LookupError):
            catalog_service.update_identity_legal_name(9999, "Ghost")
