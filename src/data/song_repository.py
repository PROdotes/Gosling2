import sqlite3
from typing import List, Optional, Mapping, Any, Dict
from src.models.domain import Song
from src.data.media_source_repository import MediaSourceRepository
from src.data.tag_repository import TagRepository
from src.data.song_album_repository import SongAlbumRepository
from src.data.publisher_repository import PublisherRepository
from src.data.song_credit_repository import SongCreditRepository
from src.services.logger import logger


class SongRepository(MediaSourceRepository):
    """Repository for loading Song domain models from the SQLite database."""

    # The Golden Truth: All song queries MUST fetch these columns.
    _COLUMNS = """
        m.SourceID, m.TypeID, m.SourcePath, m.SourceDuration, m.AudioHash,
        m.ProcessingStatus, m.IsActive, m.SourceNotes, m.MediaName,
        s.TempoBPM, s.RecordingYear, s.ISRC
    """
    _JOIN = "FROM MediaSources m JOIN Songs s ON m.SourceID = s.SourceID AND m.TypeID = (SELECT TypeID FROM Types WHERE TypeName = 'Song') AND m.IsDeleted = 0"

    def insert(self, song: Song, conn: sqlite3.Connection) -> int:
        """
        Atomic insert into MediaSources, Songs, and all relationship tables.
        Modular: delegates core MediaSource record to parent, relationships to specialized repos.
        Returns the new SourceID.
        """
        logger.debug(
            f"[SongRepository] -> insert(name='{song.title}', path='{song.source_path}')"
        )

        # 1. Insert core record (delegated to MediaSourceRepository)
        source_id = self.insert_source(song, "Song", conn)

        # 2. Insert song-specific extension record
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Songs (SourceID, TempoBPM, RecordingYear, ISRC)
            VALUES (?, ?, ?, ?)
            """,
            (source_id, song.bpm, song.year, song.isrc),
        )

        # 3. Insert relationship data
        tag_repo = TagRepository(self.db_path)
        album_repo = SongAlbumRepository(self.db_path)
        pub_repo = PublisherRepository(self.db_path)
        credit_repo = SongCreditRepository(self.db_path)

        credit_repo.insert_credits(source_id, song.credits, conn)
        tag_repo.insert_tags(source_id, song.tags, conn)
        album_repo.insert_albums(source_id, song.albums, conn)
        pub_repo.insert_song_publishers(source_id, song.publishers, conn)

        logger.info(
            f"[SongRepository] <- insert() INGESTED ID={source_id} '{song.title}'"
        )
        return source_id

    def reactivate_ghost(
        self, ghost_id: int, song: Song, conn: sqlite3.Connection
    ) -> None:
        """
        Reactivate a soft-deleted ghost song record with new metadata.
        1. Verify ghost exists and is deleted
        2. Update MediaSources (delegated to parent)
        3. Update Songs table
        4. Delete old relationships and insert new ones
        """
        logger.debug(
            f"[SongRepository] -> reactivate_ghost(id={ghost_id}, title='{song.media_name}')"
        )

        # 1. Verify ghost exists
        cursor = conn.cursor()
        cursor.execute(
            "SELECT IsDeleted FROM MediaSources WHERE SourceID = ?", (ghost_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Ghost ID {ghost_id} does not exist")
        if row[0] != 1:
            raise ValueError(f"Song ID {ghost_id} is not deleted (IsDeleted={row[0]})")

        # 2. Update MediaSources table (delegated to parent)
        self.reactivate_source(ghost_id, song, conn)

        # 2. Update Songs table
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE Songs
            SET TempoBPM = ?,
                RecordingYear = ?,
                ISRC = ?
            WHERE SourceID = ?
            """,
            (song.bpm, song.year, song.isrc, ghost_id),
        )

        # 3. Delete old relationships and insert new ones
        self.delete_song_links(ghost_id, conn)

        tag_repo = TagRepository(self.db_path)
        album_repo = SongAlbumRepository(self.db_path)
        pub_repo = PublisherRepository(self.db_path)
        credit_repo = SongCreditRepository(self.db_path)

        credit_repo.insert_credits(ghost_id, song.credits, conn)
        tag_repo.insert_tags(ghost_id, song.tags, conn)
        album_repo.insert_albums(ghost_id, song.albums, conn)
        pub_repo.insert_song_publishers(ghost_id, song.publishers, conn)

        logger.info(
            f"[SongRepository] <- reactivate_ghost() REACTIVATED ID={ghost_id} '{song.media_name}'"
        )

    def update_scalars(
        self, song_id: int, fields: dict, conn: sqlite3.Connection
    ) -> None:
        """
        Update editable scalar fields for a song. Partial updates — only send changed fields.
        Splits updates between MediaSources (media_name, is_active) and Songs (bpm, year, isrc).
        Does NOT commit.
        """
        logger.debug(
            f"[SongRepository] -> update_scalars(id={song_id}, fields={list(fields.keys())})"
        )

        media_source_fields = {
            k: v
            for k, v in fields.items()
            if k in ("media_name", "is_active", "processing_status", "source_path")
        }
        songs_fields = {k: v for k, v in fields.items() if k in ("bpm", "year", "isrc")}

        col_map = {
            "media_name": "MediaName",
            "is_active": "IsActive",
            "processing_status": "ProcessingStatus",
            "source_path": "SourcePath",
            "bpm": "TempoBPM",
            "year": "RecordingYear",
            "isrc": "ISRC",
        }

        cursor = conn.cursor()
        if media_source_fields:
            set_clause = ", ".join(f"{col_map[k]} = ?" for k in media_source_fields)
            cursor.execute(
                f"UPDATE MediaSources SET {set_clause} WHERE SourceID = ?",
                (*media_source_fields.values(), song_id),
            )

        if songs_fields:
            set_clause = ", ".join(f"{col_map[k]} = ?" for k in songs_fields)
            cursor.execute(
                f"UPDATE Songs SET {set_clause} WHERE SourceID = ?",
                (*songs_fields.values(), song_id),
            )

        logger.debug(f"[SongRepository] <- update_scalars(id={song_id}) done")

    def get_by_id(self, song_id: int) -> Optional[Song]:
        """Fetch a single Song by its SourceID."""
        logger.debug(f"[SongRepository] -> get_by_id(id={song_id})")
        results = self.get_by_ids([song_id])
        song = results[0] if results else None
        if song:
            logger.debug(f"[SongRepository] <- get_by_id(id={song_id}) '{song.title}'")
        else:
            logger.debug(f"[SongRepository] <- get_by_id(id={song_id}) NOT_FOUND")
        return song

    def get_by_ids(self, ids: List[int]) -> List[Song]:
        """Batch-fetch multiple Songs by their IDs."""
        if not ids:
            return []

        logger.debug(f"[SongRepository] Batch-fetching {len(ids)} songs.")
        placeholders = ",".join(["?" for _ in ids])
        query = (
            f"SELECT {self._COLUMNS} {self._JOIN} WHERE m.SourceID IN ({placeholders})"
        )

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, ids).fetchall()
            logger.debug(
                f"[SongRepository] Found {len(rows)} out of {len(ids)} requested songs."
            )
            return [self._row_to_song(row) for row in rows]

    def get_by_title(self, query: str) -> List[Song]:
        """Find songs by title match."""
        logger.debug(f"[SongRepository] Searching for songs with title LIKE: {query}")
        query_sql = f"SELECT {self._COLUMNS} {self._JOIN} WHERE m.MediaName LIKE ?"

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, (f"%{query}%",)).fetchall()
            logger.debug(
                f"[SongRepository] Found {len(rows)} matches for query: '{query}'"
            )
            return [self._row_to_song(row) for row in rows]

    def search_slim(self, query: str) -> List[dict]:
        """
        Fast list-view query. Returns dicts with only the fields needed for
        card rendering + the detail loading skeleton. No hydration.
        Covers the same search scope as search() via the same UNION subquery.
        """
        logger.debug(f"[SongRepository] -> search_slim(query='{query}')")
        fmt_q = f"%{query}%"

        query_sql = """
            SELECT
                m.SourceID, m.MediaName, m.SourcePath, m.SourceDuration, m.ProcessingStatus,
                s.RecordingYear, s.TempoBPM, s.ISRC, m.IsActive,
                GROUP_CONCAT(DISTINCT an.DisplayName) FILTER (WHERE r.RoleName = 'Performer') AS DisplayArtist,
                MIN(t.TagName) FILTER (WHERE t.TagCategory = 'Genre' AND mst.IsPrimary = 1) AS PrimaryGenre
            FROM MediaSources m
            JOIN Songs s ON m.SourceID = s.SourceID
                AND m.TypeID = (SELECT TypeID FROM Types WHERE TypeName = 'Song')
                AND m.IsDeleted = 0
            LEFT JOIN SongCredits sc ON m.SourceID = sc.SourceID
            LEFT JOIN ArtistNames an ON sc.CreditedNameID = an.NameID AND an.IsDeleted = 0
            LEFT JOIN Roles r ON sc.RoleID = r.RoleID
            LEFT JOIN MediaSourceTags mst ON m.SourceID = mst.SourceID
            LEFT JOIN Tags t ON mst.TagID = t.TagID AND t.IsDeleted = 0
            WHERE m.SourceID IN (
                SELECT m2.SourceID FROM MediaSources m2
                    WHERE m2.MediaName LIKE ? AND m2.IsDeleted = 0
                UNION
                SELECT sa.SourceID FROM SongAlbums sa
                    JOIN Albums a ON sa.AlbumID = a.AlbumID
                    WHERE a.AlbumTitle LIKE ? AND a.IsDeleted = 0
                UNION
                SELECT sc2.SourceID FROM SongCredits sc2
                    JOIN ArtistNames an2 ON sc2.CreditedNameID = an2.NameID
                    WHERE an2.DisplayName LIKE ? AND an2.IsDeleted = 0
                UNION
                SELECT sc3.SourceID FROM SongCredits sc3
                    JOIN ArtistNames an3 ON sc3.CreditedNameID = an3.NameID
                    JOIN Identities i ON an3.OwnerIdentityID = i.IdentityID
                    WHERE i.LegalName LIKE ? AND i.IsDeleted = 0
                UNION
                SELECT rp.SourceID FROM RecordingPublishers rp
                    JOIN Publishers p ON rp.PublisherID = p.PublisherID
                    WHERE p.PublisherName LIKE ? AND p.IsDeleted = 0
                UNION
                SELECT mst2.SourceID FROM MediaSourceTags mst2
                    JOIN Tags t2 ON mst2.TagID = t2.TagID
                    WHERE t2.TagName LIKE ? AND t2.IsDeleted = 0
                UNION
                SELECT s2.SourceID FROM Songs s2
                    WHERE CAST(s2.RecordingYear AS TEXT) LIKE ?
                       OR s2.ISRC LIKE ?
            )
            GROUP BY m.SourceID
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, (fmt_q,) * 8).fetchall()
            logger.debug(
                f"[SongRepository] <- search_slim(query='{query}') found {len(rows)}"
            )
            return [dict(row) for row in rows]

    def search_slim_by_ids(self, ids: List[int]) -> List[dict]:
        """Fetch slim list-view rows for a specific set of SourceIDs."""
        if not ids:
            return []
        placeholders = ",".join(["?" for _ in ids])
        query_sql = f"""
            SELECT
                m.SourceID, m.MediaName, m.SourcePath, m.SourceDuration, m.ProcessingStatus,
                s.RecordingYear, s.TempoBPM, s.ISRC, m.IsActive,
                GROUP_CONCAT(DISTINCT an.DisplayName) FILTER (WHERE r.RoleName = 'Performer') AS DisplayArtist,
                MIN(t.TagName) FILTER (WHERE t.TagCategory = 'Genre' AND mst.IsPrimary = 1) AS PrimaryGenre
            FROM MediaSources m
            JOIN Songs s ON m.SourceID = s.SourceID
                AND m.TypeID = (SELECT TypeID FROM Types WHERE TypeName = 'Song')
                AND m.IsDeleted = 0
            LEFT JOIN SongCredits sc ON m.SourceID = sc.SourceID
            LEFT JOIN ArtistNames an ON sc.CreditedNameID = an.NameID AND an.IsDeleted = 0
            LEFT JOIN Roles r ON sc.RoleID = r.RoleID
            LEFT JOIN MediaSourceTags mst ON m.SourceID = mst.SourceID
            LEFT JOIN Tags t ON mst.TagID = t.TagID AND t.IsDeleted = 0
            WHERE m.SourceID IN ({placeholders})
            GROUP BY m.SourceID
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, ids).fetchall()
            logger.debug(f"[SongRepository] <- search_slim_by_ids() found {len(rows)}")
            return [dict(row) for row in rows]

    def get_by_identity_ids(self, identity_ids: List[int]) -> List[Song]:
        """Retrieves songs where any given Identity ID is credited (The Grohlton Check base)."""
        if not identity_ids:
            return []

        logger.debug(f"[SongRepository] get_by_identity_ids entry: ids={identity_ids}")
        placeholders = ",".join(["?" for _ in identity_ids])
        query_sql = f"""
            SELECT {self._COLUMNS} {self._JOIN}
            WHERE m.SourceID IN (
                SELECT sc.SourceID FROM SongCredits sc
                JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
                WHERE an.OwnerIdentityID IN ({placeholders}) AND an.IsDeleted = 0
            )
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, identity_ids).fetchall()
            return [self._row_to_song(row) for row in rows]

    def get_by_hash(self, audio_hash: str) -> Optional[Song]:
        """Fetch a Song by its audio-only hash, utilizing universal MediaSource lookup."""
        logger.debug(f"[SongRepository] -> get_by_hash(hash='{audio_hash}')")
        base = super().get_by_hash(audio_hash)
        if base and base.id is not None:
            return self.get_by_id(base.id)
        return None

    def get_by_path(self, path: str) -> Optional[Song]:
        """Fetch a song by its absolute source path, utilizing universal MediaSource lookup."""
        if not path:
            return None

        logger.debug(f"[SongRepository] -> get_by_path(path='{path}')")
        base = super().get_by_path(path)
        if base and base.id is not None:
            return self.get_by_id(base.id)
        return None

    def find_by_metadata(
        self, title: str, artists: List[str], year: Optional[int]
    ) -> List[Song]:
        """
        Find songs matching Title, exact Performer set, and Recording Year.
        """
        if not title or not artists:
            return []

        logger.debug(
            f"[SongRepository] -> find_by_metadata(title='{title}', artists={artists}, year={year})"
        )

        # Step 1: Find all songs with this Title (and RecordingYear if provided)
        # This is our candidate set.
        params: List[Any] = [title]
        year_filter = ""
        if year:
            year_filter = "AND s.RecordingYear = ?"
            params.append(year)

        query_sql = f"""
            SELECT DISTINCT {self._COLUMNS}
            {self._JOIN}
            WHERE m.MediaName = ? COLLATE UTF8_NOCASE
            {year_filter}
        """

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, tuple(params)).fetchall()
            candidates = [self._row_to_song(row) for row in rows]

        if not candidates:
            return []

        # Step 2: For each candidate, check if the Performer set matches exactly
        # We need to hydrate the candidates (or at least their credits)
        # But for this simple check, we can just fetch the names from the DB for these candidates.
        found_matches = []
        candidate_ids = [c.id for c in candidates if c.id is not None]
        if not candidate_ids:
            return []
        placeholders = ",".join(["?" for _ in candidate_ids])

        performer_sql = f"""
            SELECT sc.SourceID, an.DisplayName 
            FROM SongCredits sc
            JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
            WHERE sc.SourceID IN ({placeholders})
              AND sc.RoleID = (SELECT RoleID FROM Roles WHERE RoleName = 'Performer')
              AND an.IsDeleted = 0
        """

        source_performers: Dict[int, List[str]] = {}
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            p_rows = conn.execute(performer_sql, candidate_ids).fetchall()
            for r in p_rows:
                source_performers.setdefault(r["SourceID"], []).append(r["DisplayName"])

        # Compare sets
        target_set = set(a.lower() for a in artists)
        for song in candidates:
            if song.id is None:
                continue
            current_set = set(a.lower() for a in source_performers.get(song.id, []))
            if current_set == target_set:
                found_matches.append(song)

        logger.debug(
            f"[SongRepository] <- find_by_metadata(title='{title}') matches={len(found_matches)}"
        )
        return found_matches

    def _row_to_song(self, row: Mapping[str, Any]) -> Song:
        """Map a database row to a Song Pydantic model."""
        return Song(
            id=row["SourceID"],
            type_id=row["TypeID"],
            source_path=row["SourcePath"],
            duration_s=float(row["SourceDuration"] or 0),
            audio_hash=row["AudioHash"],
            processing_status=row["ProcessingStatus"],
            is_active=bool(row["IsActive"]) if row["IsActive"] is not None else False,
            notes=row["SourceNotes"],
            media_name=row["MediaName"],
            bpm=row["TempoBPM"],
            year=row["RecordingYear"],
            isrc=row["ISRC"],
        )
