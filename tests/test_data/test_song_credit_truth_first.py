
from src.data.song_credit_repository import SongCreditRepository

class TestSongCreditTruthFirst:
    def test_add_credit_with_explicit_identity_id(self, populated_db):
        """
        Add a credit with a specific identity ID.
        In populated_db, identity 1 is Dave Grohl.
        ArtistName ID 10 is 'Dave Grohl' linked to Identity 1.
        
        We will link a new name 'David Grohl' to Identity 1.
        """
        repo = SongCreditRepository(populated_db)
        
        # Identity 1 is Dave Grohl (Person)
        identity_id = 1
        display_name = "David Grohl"
        role_name = "Performer"
        song_id = 7
        
        with repo._get_connection() as conn:
            result = repo.add_credit(song_id, display_name, role_name, conn, identity_id=identity_id)
            conn.commit()

        assert result.identity_id == identity_id
        assert result.display_name == display_name
        
        # Verify ArtistNames table has the link
        with repo._get_connection() as conn:
            row = conn.execute(
                "SELECT OwnerIdentityID FROM ArtistNames WHERE NameID = ?", (result.name_id,)
            ).fetchone()
            assert row[0] == identity_id
            
        # Verify it didn't mess with the primary name
        with repo._get_connection() as conn:
            row = conn.execute(
                "SELECT DisplayName FROM ArtistNames WHERE OwnerIdentityID = ? AND IsPrimaryName = 1", (identity_id,)
            ).fetchone()
            assert row[0] == "Dave Grohl"
