import sqlite3
from src.services.catalog_service import CatalogService
from tests.conftest import _connect  # Use gosling-aware connector


class TestSongDeletionIntegrity:
    """
    Exhaustive integration tests for the 'Pruning' side of the library lifecycle.
    Ensures that Deletes are surgical: purging relationship data while preserving shared entities.
    """

    def test_delete_song_purges_junction_tables_but_preserves_shared_entities(
        self, populated_db
    ):
        """
        Scenario: Delete Song 1 (Smells Like Teen Spirit).
        Verify:
        1. Song 1 is gone from MediaSources/Songs.
        2. Song 1 rows are gone from SongCredits, SongAlbums, SongTags, SongPublishers.
        3. Identity 2 (Nirvana) and Album 100 (Nevermind) are PRESERVED.
        """
        service = CatalogService(populated_db)
        song_id = 1

        # 0. Setup/Sanity: Verify data exists before delete
        conn = _connect(populated_db)
        try:
            conn.row_factory = sqlite3.Row
            # Check core
            assert (
                conn.execute(
                    "SELECT 1 FROM Songs WHERE SourceID = ?", (song_id,)
                ).fetchone()
                is not None
            ), "Sanity: Song 1 should exist before delete"
            # Check junctions
            assert (
                conn.execute(
                    "SELECT count(*) as count FROM SongCredits WHERE SourceID = ?",
                    (song_id,),
                ).fetchone()["count"]
                > 0
            ), "Sanity: Song 1 should have SongCredits before delete"
            assert (
                conn.execute(
                    "SELECT count(*) as count FROM SongAlbums WHERE SourceID = ?",
                    (song_id,),
                ).fetchone()["count"]
                > 0
            ), "Sanity: Song 1 should have SongAlbums before delete"
            assert (
                conn.execute(
                    "SELECT count(*) as count FROM MediaSourceTags WHERE SourceID = ?",
                    (song_id,),
                ).fetchone()["count"]
                > 0
            ), "Sanity: Song 1 should have MediaSourceTags before delete"
            assert (
                conn.execute(
                    "SELECT count(*) as count FROM RecordingPublishers WHERE SourceID = ?",
                    (song_id,),
                ).fetchone()["count"]
                > 0
            ), "Sanity: Song 1 should have RecordingPublishers before delete"

            # Check shared entities
            album_id = 100  # Nevermind
            identity_id = 2  # Nirvana
            assert (
                conn.execute(
                    "SELECT 1 FROM Albums WHERE AlbumID = ?", (album_id,)
                ).fetchone()
                is not None
            ), "Sanity: Album 100 (Nevermind) should exist before delete"
            assert (
                conn.execute(
                    "SELECT 1 FROM Identities WHERE IdentityID = ?", (identity_id,)
                ).fetchone()
                is not None
            ), "Sanity: Identity 2 (Nirvana) should exist before delete"
        finally:
            conn.close()

        # 1. Action: Delete via Service
        success = service.delete_song(song_id)
        assert success is True, f"Expected delete_song({song_id}) to return True"

        # 2. Assertions: Purgatory (Core)
        conn = _connect(populated_db)
        try:
            conn.row_factory = sqlite3.Row

            # CORE TABLES (Marked for later restoration, but hidden from surface)
            res = conn.execute(
                "SELECT IsDeleted FROM MediaSources WHERE SourceID = ?", (song_id,)
            ).fetchone()
            assert res is not None, "Song record should persist in MediaSources (soft-delete)"
            assert (
                res["IsDeleted"] == 1
            ), f"Expected IsDeleted=1 for song {song_id}, got {res['IsDeleted']}"

            assert (
                conn.execute(
                    "SELECT 1 FROM Songs WHERE SourceID = ?", (song_id,)
                ).fetchone()
                is not None
            ), "Song extension record should persist in Songs (soft-delete)"

            # JUNCTION TABLES (The Scars)
            assert (
                conn.execute(
                    "SELECT count(*) as count FROM SongCredits WHERE SourceID = ?",
                    (song_id,),
                ).fetchone()["count"]
                == 0
            ), "SongCredits junction rows leaked"
            assert (
                conn.execute(
                    "SELECT count(*) as count FROM SongAlbums WHERE SourceID = ?",
                    (song_id,),
                ).fetchone()["count"]
                == 0
            ), "SongAlbums junction rows leaked"
            assert (
                conn.execute(
                    "SELECT count(*) as count FROM MediaSourceTags WHERE SourceID = ?",
                    (song_id,),
                ).fetchone()["count"]
                == 0
            ), "MediaSourceTags junction rows leaked"
            assert (
                conn.execute(
                    "SELECT count(*) as count FROM RecordingPublishers WHERE SourceID = ?",
                    (song_id,),
                ).fetchone()["count"]
                == 0
            ), "RecordingPublishers junction rows leaked"

            # NEGATIVE ISOLATION (Safe Entities)
            assert (
                conn.execute(
                    "SELECT AlbumTitle FROM Albums WHERE AlbumID = ?", (album_id,)
                ).fetchone()["AlbumTitle"]
                == "Nevermind"
            ), "Shared Album was accidentally deleted"
            assert (
                conn.execute(
                    "SELECT 1 FROM Identities WHERE IdentityID = ?", (identity_id,)
                ).fetchone()
                is not None
            ), "Shared Identity was accidentally deleted"

            # Check other songs remain
            assert (
                conn.execute("SELECT 1 FROM Songs WHERE SourceID = 2").fetchone()
                is not None
            ), "Deletion leaked! Song 2 was accidentally removed"
        finally:
            conn.close()

    def test_delete_song_with_no_secondary_data_works(self, empty_db):
        """Verify deletion logic doesn't crash on an 'Anemic' song record (no tags/credits)."""
        # We need to manually insert a minimal song into empty_db
        conn = _connect(empty_db)
        try:
            # 1. SETUP CRITICAL INFRASTRUCTURE (Types)
            # Repo join fails if Types row is missing!
            conn.execute("INSERT INTO Types (TypeID, TypeName) VALUES (1, 'Song')")

            # 2. Setup record
            conn.execute(
                "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath) VALUES (999, 1, 'Anemic', '/path/999')"
            )
            conn.execute("INSERT INTO Songs (SourceID) VALUES (999)")
            conn.commit()
        finally:
            conn.close()

        service = CatalogService(empty_db)
        success = service.delete_song(999)
        assert success is True, f"Expected True, got {success}"

        # Verify song is marked deleted
        conn = _connect(empty_db)
        try:
            conn.row_factory = sqlite3.Row
            res = conn.execute(
                "SELECT IsDeleted FROM MediaSources WHERE SourceID = 999"
            ).fetchone()
            assert (
                res is not None and res["IsDeleted"] == 1
            ), "Expected Song 999 to be soft-deleted in MediaSources"
            assert (
                conn.execute("SELECT 1 FROM Songs WHERE SourceID = 999").fetchone()
                is not None
            ), "Expected Song 999 extension to remain in Songs"
        finally:
            conn.close()

    def test_delete_lone_song_preserves_orphaned_metadata_entities(self, empty_db):
        """
        Scenario: A 'Lone Song' (888) is the ONLY record linked to a unique Identity, Album, Tag, and Publisher.
        Verify:
        1. Deleting the song PURGES junctions.
        2. Deleting the song PRESERVES the entities themselves (Orphans are kept in the catalog).
        """
        # 1. SETUP UNIQUE ISLAND
        # We need IDs that won't collide
        SID, TID, AID, IID, NID, PID, RID = 888, 777, 666, 555, 444, 333, 1

        conn = _connect(empty_db)
        try:
            # Entities
            conn.execute("INSERT INTO Types (TypeID, TypeName) VALUES (1, 'Song')")
            conn.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (1, 'Performer')")
            conn.execute(
                "INSERT INTO Identities (IdentityID, IdentityType) VALUES (?, 'person')",
                (IID,),
            )
            conn.execute(
                "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName) VALUES (?, ?, 'Lone Artist')",
                (NID, IID),
            )
            conn.execute(
                "INSERT INTO Albums (AlbumID, AlbumTitle) VALUES (?, 'Lone Album')",
                (AID,),
            )
            conn.execute(
                "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (?, 'Lone Tag', 'Genre')",
                (TID,),
            )
            conn.execute(
                "INSERT INTO Publishers (PublisherID, PublisherName) VALUES (?, 'Lone Publisher')",
                (PID,),
            )

            # Core Song
            conn.execute(
                "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath) VALUES (?, 1, 'Lone Song', '/lone/path')",
                (SID,),
            )
            conn.execute("INSERT INTO Songs (SourceID) VALUES (?)", (SID,))

            # Relationships (Junctions)
            conn.execute(
                "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
                (SID, NID, RID),
            )
            conn.execute(
                "INSERT INTO SongAlbums (SourceID, AlbumID) VALUES (?, ?)", (SID, AID)
            )
            conn.execute(
                "INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)",
                (SID, TID),
            )
            conn.execute(
                "INSERT INTO RecordingPublishers (SourceID, PublisherID) VALUES (?, ?)",
                (SID, PID),
            )

            # Album Context (Should stay if Album stays)
            conn.execute(
                "INSERT INTO AlbumPublishers (AlbumID, PublisherID) VALUES (?, ?)",
                (AID, PID),
            )
            conn.execute(
                "INSERT INTO AlbumCredits (AlbumID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
                (AID, NID, RID),
            )

            conn.commit()
        finally:
            conn.close()

        service = CatalogService(empty_db)

        # 2. ACTION: Delete Lone Survivor
        success = service.delete_song(SID)
        assert success is True, f"Expected True, got {success}"

        # 3. VERIFY SURGICAL DESTRUCTION
        conn = _connect(empty_db)
        try:
            conn.row_factory = sqlite3.Row

            # HIDDEN: The Song record is marked deleted
            res = conn.execute(
                "SELECT IsDeleted FROM MediaSources WHERE SourceID = ?", (SID,)
            ).fetchone()
            assert (
                res is not None and res["IsDeleted"] == 1
            ), "Expected MediaSources row to be soft-deleted"
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM SongCredits WHERE SourceID = ?", (SID,)
                ).fetchone()["c"]
                == 0
            ), "Expected SongCredits to be purged"
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM SongAlbums WHERE SourceID = ?", (SID,)
                ).fetchone()["c"]
                == 0
            ), "Expected SongAlbums to be purged"
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM MediaSourceTags WHERE SourceID = ?",
                    (SID,),
                ).fetchone()["c"]
                == 0
            ), "Expected MediaSourceTags to be purged"
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM RecordingPublishers WHERE SourceID = ?",
                    (SID,),
                ).fetchone()["c"]
                == 0
            ), "Expected RecordingPublishers to be purged"

            # PRESERVED: The objects themselves (The Catalog Knowledge)
            assert (
                conn.execute(
                    "SELECT DisplayName FROM ArtistNames WHERE NameID = ?", (NID,)
                ).fetchone()["DisplayName"]
                == "Lone Artist"
            ), "Expected orphaned ArtistName 'Lone Artist' to be preserved"
            assert (
                conn.execute(
                    "SELECT AlbumTitle FROM Albums WHERE AlbumID = ?", (AID,)
                ).fetchone()["AlbumTitle"]
                == "Lone Album"
            ), "Expected orphaned Album 'Lone Album' to be preserved"
            assert (
                conn.execute(
                    "SELECT TagName FROM Tags WHERE TagID = ?", (TID,)
                ).fetchone()["TagName"]
                == "Lone Tag"
            ), "Expected orphaned Tag 'Lone Tag' to be preserved"
            assert (
                conn.execute(
                    "SELECT PublisherName FROM Publishers WHERE PublisherID = ?", (PID,)
                ).fetchone()["PublisherName"]
                == "Lone Publisher"
            ), "Expected orphaned Publisher 'Lone Publisher' to be preserved"

            # PRESERVED: Indirect relations (Album metadata)
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM AlbumPublishers WHERE AlbumID = ?",
                    (AID,),
                ).fetchone()["c"]
                == 1
            ), "Expected AlbumPublishers row to be preserved"
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM AlbumCredits WHERE AlbumID = ?", (AID,)
                ).fetchone()["c"]
                == 1
            ), "Expected AlbumCredits row to be preserved"
        finally:
            conn.close()

    def test_delete_song_preserves_shared_metadata_for_others(self, empty_db):
        """
        Scenario: Song A (111) and Song B (222) share a Tag and a Publisher.
        Verify: Deleting Song A does NOT break Song B's connections.
        """
        # IDs
        S_A, S_B, TAG, PUB = 111, 222, 99, 88

        conn = _connect(empty_db)
        try:
            conn.execute("INSERT INTO Types (TypeID, TypeName) VALUES (1, 'Song')")
            # Shared Metadata
            conn.execute(
                "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (?, 'Shared Tag', 'Genre')",
                (TAG,),
            )
            conn.execute(
                "INSERT INTO Publishers (PublisherID, PublisherName) VALUES (?, 'Shared Pub')",
                (PUB,),
            )

            # Two Songs
            conn.execute(
                "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath) VALUES (?, 1, 'Song A', '/path/a')",
                (S_A,),
            )
            conn.execute("INSERT INTO Songs (SourceID) VALUES (?)", (S_A,))
            conn.execute(
                "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath) VALUES (?, 1, 'Song B', '/path/b')",
                (S_B,),
            )
            conn.execute("INSERT INTO Songs (SourceID) VALUES (?)", (S_B,))

            # Shared Junctions
            conn.execute(
                "INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)",
                (S_A, TAG),
            )
            conn.execute(
                "INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)",
                (S_B, TAG),
            )
            conn.execute(
                "INSERT INTO RecordingPublishers (SourceID, PublisherID) VALUES (?, ?)",
                (S_A, PUB),
            )
            conn.execute(
                "INSERT INTO RecordingPublishers (SourceID, PublisherID) VALUES (?, ?)",
                (S_B, PUB),
            )
            conn.commit()
        finally:
            conn.close()

        service = CatalogService(empty_db)

        # ACTION: Delete Song A
        success = service.delete_song(S_A)
        assert (
            success is True
        ), f"Expected delete_song({S_A}) to return True, got {success}"

        # VERIFY: B is still linked
        conn = _connect(empty_db)
        try:
            conn.row_factory = sqlite3.Row
            # A links are gone
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM MediaSourceTags WHERE SourceID = ?",
                    (S_A,),
                ).fetchone()["c"]
                == 0
            ), "Expected Song A's MediaSourceTags to be purged"
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM RecordingPublishers WHERE SourceID = ?",
                    (S_A,),
                ).fetchone()["c"]
                == 0
            ), "Expected Song A's RecordingPublishers to be purged"

            # B links are STILL THERE
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM MediaSourceTags WHERE SourceID = ?",
                    (S_B,),
                ).fetchone()["c"]
                == 1
            ), "Expected Song B's MediaSourceTags to survive"
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM RecordingPublishers WHERE SourceID = ?",
                    (S_B,),
                ).fetchone()["c"]
                == 1
            ), "Expected Song B's RecordingPublishers to survive"

            # Metadata still exists
            assert (
                conn.execute("SELECT 1 FROM Tags WHERE TagID = ?", (TAG,)).fetchone()
                is not None
            ), "Expected shared Tag to be preserved"
        finally:
            conn.close()

    def test_delete_triangle_isolation_rigor(self, empty_db):
        """
        Ultimate Rigor: 3 Songs.
        Song 1: Unique Island.
        Song 2 & 3: Shared Cluster.
        Delete Song 1 & 2.
        Song 3 must survive with all its links intact.
        Unique metadata from Song 1 must survive as orphans.
        """
        # IDs for Song 1 (Island)
        S1, A1, I1, N1, P1, T1 = 101, 201, 301, 601, 401, 501
        # IDs for Shared Cluster (Song 2 & 3)
        S2, S3, AS, IS, NS, PS, TS = 102, 103, 202, 302, 602, 402, 502
        ROLE = 1

        conn = _connect(empty_db)
        try:
            conn.execute("INSERT INTO Types (TypeID, TypeName) VALUES (1, 'Song')")
            conn.execute("INSERT INTO Roles (RoleID, RoleName) VALUES (1, 'Performer')")

            # --- SETUP ISLAND (SONG 1) ---
            conn.execute(
                "INSERT INTO Identities (IdentityID, IdentityType) VALUES (?, 'person')",
                (I1,),
            )
            conn.execute(
                "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName) VALUES (?, ?, 'Artist 1')",
                (N1, I1),
            )
            conn.execute(
                "INSERT INTO Albums (AlbumID, AlbumTitle) VALUES (?, 'Album 1')", (A1,)
            )
            conn.execute(
                "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (?, 'Tag 1', 'Genre')",
                (T1,),
            )
            conn.execute(
                "INSERT INTO Publishers (PublisherID, PublisherName) VALUES (?, 'Pub 1')",
                (P1,),
            )
            conn.execute(
                "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath) VALUES (?, 1, 'Song 1', '/s/1')",
                (S1,),
            )
            conn.execute("INSERT INTO Songs (SourceID) VALUES (?)", (S1,))
            conn.execute(
                "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
                (S1, N1, ROLE),
            )
            conn.execute(
                "INSERT INTO SongAlbums (SourceID, AlbumID) VALUES (?, ?)", (S1, A1)
            )
            conn.execute(
                "INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)", (S1, T1)
            )
            conn.execute(
                "INSERT INTO RecordingPublishers (SourceID, PublisherID) VALUES (?, ?)",
                (S1, P1),
            )

            # --- SETUP CLUSTER (SONG 2 & 3) ---
            conn.execute(
                "INSERT INTO Identities (IdentityID, IdentityType) VALUES (?, 'person')",
                (IS,),
            )
            conn.execute(
                "INSERT INTO ArtistNames (NameID, OwnerIdentityID, DisplayName) VALUES (?, ?, 'Shared Artist')",
                (NS, IS),
            )
            conn.execute(
                "INSERT INTO Albums (AlbumID, AlbumTitle) VALUES (?, 'Shared Album')",
                (AS,),
            )
            conn.execute(
                "INSERT INTO Tags (TagID, TagName, TagCategory) VALUES (?, 'Shared Tag', 'Genre')",
                (TS,),
            )
            conn.execute(
                "INSERT INTO Publishers (PublisherID, PublisherName) VALUES (?, 'Shared Pub')",
                (PS,),
            )

            for sid, name, path in [(S2, "Song 2", "/s/2"), (S3, "Song 3", "/s/3")]:
                conn.execute(
                    "INSERT INTO MediaSources (SourceID, TypeID, MediaName, SourcePath) VALUES (?, 1, ?, ?)",
                    (sid, name, path),
                )
                conn.execute("INSERT INTO Songs (SourceID) VALUES (?)", (sid,))
                conn.execute(
                    "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
                    (sid, NS, ROLE),
                )
                conn.execute(
                    "INSERT INTO SongAlbums (SourceID, AlbumID) VALUES (?, ?)",
                    (sid, AS),
                )
                conn.execute(
                    "INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)",
                    (sid, TS),
                )
                conn.execute(
                    "INSERT INTO RecordingPublishers (SourceID, PublisherID) VALUES (?, ?)",
                    (sid, PS),
                )

            conn.commit()
        finally:
            conn.close()

        service = CatalogService(empty_db)

        # ACTION: Delete Song 1 (Island) and Song 2 (Shared)
        service.delete_song(S1)
        service.delete_song(S2)

        # VERIFY RESULTS
        conn = _connect(empty_db)
        try:
            conn.row_factory = sqlite3.Row

            # 1. CHECK HIDDEN (S1 & S2)
            for sid in [S1, S2]:
                res = conn.execute(
                    "SELECT IsDeleted FROM MediaSources WHERE SourceID = ?", (sid,)
                ).fetchone()
                assert (
                    res is not None and res["IsDeleted"] == 1
                ), f"Expected Song {sid} to be soft-deleted in MediaSources"
                assert (
                    conn.execute(
                        "SELECT count(*) as c FROM SongCredits WHERE SourceID = ?",
                        (sid,),
                    ).fetchone()["c"]
                    == 0
                ), f"Expected Song {sid} SongCredits to be purged"
                assert (
                    conn.execute(
                        "SELECT count(*) as c FROM SongAlbums WHERE SourceID = ?",
                        (sid,),
                    ).fetchone()["c"]
                    == 0
                ), f"Expected Song {sid} SongAlbums to be purged"
                assert (
                    conn.execute(
                        "SELECT count(*) as c FROM MediaSourceTags WHERE SourceID = ?",
                        (sid,),
                    ).fetchone()["c"]
                    == 0
                ), f"Expected Song {sid} MediaSourceTags to be purged"
                assert (
                    conn.execute(
                        "SELECT count(*) as c FROM RecordingPublishers WHERE SourceID = ?",
                        (sid,),
                    ).fetchone()["c"]
                    == 0
                ), f"Expected Song {sid} RecordingPublishers to be purged"

            # 2. CHECK SURVIVOR (S3)
            assert (
                conn.execute(
                    "SELECT 1 FROM MediaSources WHERE SourceID = ?", (S3,)
                ).fetchone()
                is not None
            ), "Expected Song 3 to survive in MediaSources"
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM SongCredits WHERE SourceID = ?", (S3,)
                ).fetchone()["c"]
                == 1
            ), "Expected Song 3 to retain 1 SongCredits row"
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM SongAlbums WHERE SourceID = ?", (S3,)
                ).fetchone()["c"]
                == 1
            ), "Expected Song 3 to retain 1 SongAlbums row"
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM MediaSourceTags WHERE SourceID = ?",
                    (S3,),
                ).fetchone()["c"]
                == 1
            ), "Expected Song 3 to retain 1 MediaSourceTags row"
            assert (
                conn.execute(
                    "SELECT count(*) as c FROM RecordingPublishers WHERE SourceID = ?",
                    (S3,),
                ).fetchone()["c"]
                == 1
            ), "Expected Song 3 to retain 1 RecordingPublishers row"

            # 3. CHECK CATALOG PRESERVATION (Orphans)
            assert (
                conn.execute(
                    "SELECT AlbumTitle FROM Albums WHERE AlbumID = ?", (A1,)
                ).fetchone()["AlbumTitle"]
                == "Album 1"
            ), "Expected orphaned Album 'Album 1' to be preserved"
            assert (
                conn.execute(
                    "SELECT DisplayName FROM ArtistNames WHERE NameID = ?", (N1,)
                ).fetchone()["DisplayName"]
                == "Artist 1"
            ), "Expected orphaned ArtistName 'Artist 1' to be preserved"
            assert (
                conn.execute(
                    "SELECT TagName FROM Tags WHERE TagID = ?", (T1,)
                ).fetchone()["TagName"]
                == "Tag 1"
            ), "Expected orphaned Tag 'Tag 1' to be preserved"
            assert (
                conn.execute(
                    "SELECT PublisherName FROM Publishers WHERE PublisherID = ?", (P1,)
                ).fetchone()["PublisherName"]
                == "Pub 1"
            ), "Expected orphaned Publisher 'Pub 1' to be preserved"

            # The Shared metadata cluster MUST survive
            assert (
                conn.execute(
                    "SELECT AlbumTitle FROM Albums WHERE AlbumID = ?", (AS,)
                ).fetchone()["AlbumTitle"]
                == "Shared Album"
            ), "Expected shared Album 'Shared Album' to be preserved"
            assert (
                conn.execute(
                    "SELECT DisplayName FROM ArtistNames WHERE NameID = ?", (NS,)
                ).fetchone()["DisplayName"]
                == "Shared Artist"
            ), "Expected shared ArtistName 'Shared Artist' to be preserved"
        finally:
            conn.close()
