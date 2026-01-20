
import pytest
import tempfile
import os
from src.business.services.contributor_service import ContributorService
# We verify LAWS by checking outcomes, not implementation details.

class TestLaw001AliasIntegrity:
    """
    LAW 001: ARTIST IDENTITY INTEGRITY
    
    This test suite enforces the Immutable Laws of Artist Identity Management.
    These rules protect against data loss and navigation bugs.
    
    Any failure here indicates a CRITICAL REGRESSION in the application logic.
    DO NOT MODIFY THIS FILE TO MAKE TESTS PASS. FIX THE APPLICATION CODE.
    """
    
    @pytest.fixture
    def service(self):
        # Use a temp file so connections share state
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        svc = ContributorService(db_path=path)
        yield svc
        
        # Cleanup
        if os.path.exists(path):
            try:
                os.unlink(path)
            except:
                pass

    def test_law_unlink_must_split_not_delete(self, service):
        """
        LAW: "Removing" an alias/member must SPLIT it into a new Identity.
        It MUST NOT delete the name record (which would destroy credit history).
        """
        # 1. Setup: Gustavo (Primary)
        # Use service.create to get a proper setup (Identity + Name)
        gustavo = service.create("Gustavo", "person")
        # Gustavo.contributor_id is the NAME ID.
        
        # Add Alias "Noelle"
        # add_alias takes a ContributorID (NameID) as owner
        service.add_alias(gustavo.contributor_id, "Noelle")
        
        # Verify Noelle exists as alias
        aliases = service.get_aliases(gustavo.contributor_id) # Using NameID to lookup
        assert len(aliases) == 1
        noelle_alias_id = aliases[0].alias_id
        
        # 2. ACTION: Unlink Noelle
        # We test the unlink_alias method specifically as it is the designated tool for this law.
        success = service.unlink_alias(noelle_alias_id)
        assert success is True, "unlink_alias failed to execute"
        
        # 3. VERDICT: Did it Split?
        # A. The Name Record must still exist
        name_rec = service._name_service.get_name(noelle_alias_id)
        assert name_rec is not None, "VIOLATION: Unlinking deleted the Name record!"
        
        # B. It must have a NEW Identity
        # We need to find the old identity ID
        old_ident_id = service._get_identity_id(gustavo.contributor_id)
        assert name_rec.owner_identity_id != old_ident_id, "VIOLATION: Name was not moved to new identity"
        assert name_rec.owner_identity_id > 0, "VIOLATION: Invalid new identity ID"
        
        # C. It must be the Primary Name of the new Identity
        assert name_rec.is_primary_name is True, "VIOLATION: Name is not Primary in new identity"

    def test_law_click_redirection_data_integrity(self, service):
        """
        LAW: Every Identity containing names MUST have exactly one Primary Name.
        Failure to enforce this causes the 'Gaslighting' navigation bug (Clicking alias opens itself).
        """
        # 1. Setup: Identity with 2 names, initially valid
        gustavo = service.create("Gustavo", "person")
        service.add_alias(gustavo.contributor_id, "Gabriel")
        
        # 2. ACTION: Verify Integrity
        ident_id = service._get_identity_id(gustavo.contributor_id)
        names = service._name_service.get_by_owner(ident_id)
        primaries = [n for n in names if n.is_primary_name]
        
        # 3. VERDICT
        assert len(primaries) == 1, f"VIOLATION: Identity {ident_id} has {len(primaries)} primaries (Must be 1)"
        assert primaries[0].display_name == "Gustavo"
