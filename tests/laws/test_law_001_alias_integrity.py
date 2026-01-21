
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

    def test_law_rename_collision_detected(self, service):
        """
        LAW RULE 3: When renaming to an existing name, collision MUST be detected.
        This test verifies the collision detection works (UI prompt responsibility is separate).
        """
        # 1. Setup: Two separate artists
        artist1 = service.create("Lana Mandarić", "person")  # ć
        artist2 = service.create("Lana Mandarič", "person")  # č

        # 2. ACTION: Check collision detection when trying to rename artist1 to artist2's name
        collision = service.get_collision("Lana Mandarič", exclude_id=artist1.contributor_id)

        # 3. VERDICT: Collision MUST be detected
        assert collision is not None, "VIOLATION: Collision not detected for Unicode variant names!"
        assert collision.contributor_id == artist2.contributor_id, "VIOLATION: Wrong collision target!"
        assert collision.name == "Lana Mandarič", "VIOLATION: Collision name mismatch!"

    def test_law_consume_deletes_source(self, service):
        """
        LAW RULE 4: consume() MUST delete the source name (not keep as alias).
        This is for rename workflows where user is fixing a typo.
        """
        # 1. Setup: Two artists with same name variants
        typo = service.create("Lana Mandarić", "person")  # Typo version
        correct = service.create("Lana Mandarič", "person")  # Correct version

        typo_id = typo.contributor_id
        correct_id = correct.contributor_id

        # 2. ACTION: Consume typo into correct (rename workflow)
        success = service.consume(typo_id, correct_id)
        assert success is True, "consume() failed to execute"

        # 3. VERDICT: Source must be DELETED, not kept as alias
        # A. The typo name record must NOT exist anymore
        typo_name = service._name_service.get_name(typo_id)
        assert typo_name is None, "VIOLATION: consume() did not delete source name!"

        # B. The correct name must still exist
        correct_name = service._name_service.get_name(correct_id)
        assert correct_name is not None, "VIOLATION: consume() deleted target name!"

        # C. The correct name must NOT have the typo as an alias
        aliases = service.get_aliases(correct_id)
        alias_names = [a.alias_name for a in aliases]
        assert "Lana Mandarić" not in alias_names, "VIOLATION: consume() kept source as alias!"

    def test_law_merge_creates_alias(self, service):
        """
        LAW RULE 5: merge() MUST keep the source as an alias (not delete).
        This is for "Add Alias" workflows where user purposefully links names.
        """
        # 1. Setup: Two artists
        artist1 = service.create("Gabriele Ponte", "person")  # Full name
        artist2 = service.create("Gabry Ponte", "person")     # Stage name

        artist1_id = artist1.contributor_id
        artist2_id = artist2.contributor_id

        # 2. ACTION: Merge artist2 into artist1 (Add Alias workflow)
        success = service.merge(artist2_id, artist1_id)
        assert success is True, "merge() failed to execute"

        # 3. VERDICT: Source must be kept as an ALIAS
        # A. The stage name record must still exist
        stage_name = service._name_service.get_name(artist2_id)
        assert stage_name is not None, "VIOLATION: merge() deleted source name!"

        # B. The stage name must NOT be primary anymore
        assert stage_name.is_primary_name is False, "VIOLATION: merge() kept source as primary!"

        # C. Both names must share the same Identity
        ident1 = service._get_identity_id(artist1_id)
        ident2 = service._get_identity_id(artist2_id)
        assert ident1 == ident2, "VIOLATION: merge() did not link identities!"

        # D. The aliases list must include the stage name
        aliases = service.get_aliases(artist1_id)
        alias_names = [a.alias_name for a in aliases]
        assert "Gabry Ponte" in alias_names, "VIOLATION: merge() did not create alias relationship!"

    def test_law_unicode_handling(self, service):
        """
        UNICODE HANDLING: py_lower() must distinguish between different Unicode characters.
        ć (U+0107) and č (U+010D) are DIFFERENT characters in Croatian.
        """
        # 1. Setup: Two artists with different Unicode characters
        artist_c = service.create("Lana Mandarić", "person")  # ć = U+0107
        artist_c_caron = service.create("Lana Mandarič", "person")  # č = U+010D

        # 2. ACTION: Try to find exact match
        # Search for č should NOT find ć
        collision = service.get_collision("Lana Mandarič", exclude_id=artist_c_caron.contributor_id)

        # 3. VERDICT: They must be treated as DIFFERENT names
        assert collision is None, "VIOLATION: Unicode characters ć and č treated as identical!"

        # 4. Verify case-insensitivity still works
        collision_case = service.get_collision("lana mandarić", exclude_id=None)
        assert collision_case is not None, "VIOLATION: Case-insensitive search failed!"
        assert collision_case.contributor_id == artist_c.contributor_id
