import sqlite3
from typing import List, Optional, Mapping, Any, Dict
from src.models.domain import Song
from src.data.media_source_repository import MediaSourceRepository
from src.data.tag_repository import TagRepository
from src.data.song_album_repository import SongAlbumRepository
from src.data.publisher_repository import PublisherRepository
from src.data.song_credit_repository import SongCreditRepository
from src.services.logger import logger
from src.engine.config import ProcessingStatus

# ── Review blocker SQL fragments ─────────────────────────────────────────────
# These mirror compute_review_blockers() in view_models.py.
# If you add/remove a blocker, update BOTH places.
BLOCKER_SQL = """
    m.MediaName IS NULL OR m.MediaName = ''
    OR s.RecordingYear IS NULL
    OR NOT EXISTS (SELECT 1 FROM SongCredits sc JOIN Roles r ON sc.RoleID = r.RoleID WHERE sc.SourceID = m.SourceID AND r.RoleName = 'Performer')
    OR NOT EXISTS (SELECT 1 FROM SongCredits sc JOIN Roles r ON sc.RoleID = r.RoleID WHERE sc.SourceID = m.SourceID AND r.RoleName = 'Composer')
    OR NOT EXISTS (SELECT 1 FROM MediaSourceTags mst JOIN Tags t ON mst.TagID = t.TagID WHERE mst.SourceID = m.SourceID AND t.TagCategory = 'Genre' AND t.IsDeleted = 0)
    OR NOT EXISTS (SELECT 1 FROM RecordingPublishers rp WHERE rp.SourceID = m.SourceID)
    OR NOT EXISTS (SELECT 1 FROM SongAlbums sa WHERE sa.SourceID = m.SourceID)
"""

NO_BLOCKER_SQL = """
    m.MediaName IS NOT NULL AND m.MediaName != ''
    AND s.RecordingYear IS NOT NULL
    AND EXISTS (SELECT 1 FROM SongCredits sc JOIN Roles r ON sc.RoleID = r.RoleID WHERE sc.SourceID = m.SourceID AND r.RoleName = 'Performer')
    AND EXISTS (SELECT 1 FROM SongCredits sc JOIN Roles r ON sc.RoleID = r.RoleID WHERE sc.SourceID = m.SourceID AND r.RoleName = 'Composer')
    AND EXISTS (SELECT 1 FROM MediaSourceTags mst JOIN Tags t ON mst.TagID = t.TagID WHERE mst.SourceID = m.SourceID AND t.TagCategory = 'Genre' AND t.IsDeleted = 0)
    AND EXISTS (SELECT 1 FROM RecordingPublishers rp WHERE rp.SourceID = m.SourceID)
    AND EXISTS (SELECT 1 FROM SongAlbums sa WHERE sa.SourceID = m.SourceID)
"""
# ─────────────────────────────────────────────────────────────────────────────


class SongRepository(MediaSourceRepository):
    """Repository for loading Song domain models from the SQLite database."""

    # The Golden Truth: All song queries MUST fetch these columns.
    _COLUMNS = """
        m.SourceID, m.TypeID, m.SourcePath, m.SourceDuration, m.AudioHash,
        m.ProcessingStatus, m.IsActive, m.SourceNotes, m.MediaName,
        s.TempoBPM, s.RecordingYear, s.ISRC,
        so.OriginPath
    """
    _JOIN = "FROM MediaSources m JOIN Songs s ON m.SourceID = s.SourceID AND m.TypeID = (SELECT TypeID FROM Types WHERE TypeName = 'Song') AND m.IsDeleted = 0 LEFT JOIN StagingOrigins so ON so.SourceID = m.SourceID"

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
            if k
            in (
                "media_name",
                "is_active",
                "processing_status",
                "source_path",
                "audio_hash",
            )
        }
        songs_fields = {k: v for k, v in fields.items() if k in ("bpm", "year", "isrc")}

        col_map = {
            "media_name": "MediaName",
            "is_active": "IsActive",
            "processing_status": "ProcessingStatus",
            "source_path": "SourcePath",
            "audio_hash": "AudioHash",
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

    def get_by_id(
        self, song_id: int, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[Song]:
        """Fetch a single Song by its SourceID."""
        logger.debug(f"[SongRepository] -> get_by_id(id={song_id})")
        results = self.get_by_ids([song_id], conn)
        song = results[0] if results else None
        if song:
            logger.debug(f"[SongRepository] <- get_by_id(id={song_id}) '{song.title}'")
        else:
            logger.debug(f"[SongRepository] <- get_by_id(id={song_id}) NOT_FOUND")
        return song

    def get_by_ids(
        self, ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> List[Song]:
        """Batch-fetch multiple Songs by their IDs."""
        if not ids:
            return []

        logger.debug(f"[SongRepository] Batch-fetching {len(ids)} songs.")
        placeholders = ",".join(["?" for _ in ids])
        query = (
            f"SELECT {self._COLUMNS} {self._JOIN} WHERE m.SourceID IN ({placeholders})"
        )

        if conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, ids).fetchall()
            return [self._row_to_song(row) for row in rows]

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            rows = new_conn.execute(query, ids).fetchall()
            logger.debug(
                f"[SongRepository] Found {len(rows)} out of {len(ids)} requested songs."
            )
            return [self._row_to_song(row) for row in rows]

    def get_by_title(
        self, query: str, conn: Optional[sqlite3.Connection] = None
    ) -> List[Song]:
        """Find songs by title match."""
        logger.debug(f"[SongRepository] Searching for songs with title LIKE: {query}")
        query_sql = f"SELECT {self._COLUMNS} {self._JOIN} WHERE m.MediaName LIKE ?"

        if conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, (f"%{query}%",)).fetchall()
            return [self._row_to_song(row) for row in rows]

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            rows = new_conn.execute(query_sql, (f"%{query}%",)).fetchall()
            logger.debug(
                f"[SongRepository] Found {len(rows)} matches for query: '{query}'"
            )
            return [self._row_to_song(row) for row in rows]

    def search_slim(
        self, query: str, conn: Optional[sqlite3.Connection] = None
    ) -> List[dict]:
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
                MIN(t.TagName) FILTER (WHERE t.TagCategory = 'Genre' AND mst.IsPrimary = 1) AS PrimaryGenre,
                EXISTS (SELECT 1 FROM RecordingPublishers rp WHERE rp.SourceID = m.SourceID) AS has_publisher,
                EXISTS (SELECT 1 FROM SongAlbums sa WHERE sa.SourceID = m.SourceID) AS has_album,
                COUNT(DISTINCT sc.CreditID) FILTER (WHERE r.RoleName = 'Performer') > 0 AS has_performer,
                COUNT(DISTINCT sc.CreditID) FILTER (WHERE r.RoleName = 'Composer') > 0 AS has_composer
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
        if conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, (fmt_q,) * 8).fetchall()
            return [dict(row) for row in rows]

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            rows = new_conn.execute(query_sql, (fmt_q,) * 8).fetchall()
            logger.debug(
                f"[SongRepository] <- search_slim(query='{query}') found {len(rows)}"
            )
            return [dict(row) for row in rows]

    def search_slim_by_ids(
        self, ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> List[dict]:
        """Fetch slim list-view rows for a specific set of SourceIDs."""
        if not ids:
            return []
        placeholders = ",".join(["?" for _ in ids])
        query_sql = f"""
            SELECT
                m.SourceID, m.MediaName, m.SourcePath, m.SourceDuration, m.ProcessingStatus,
                s.RecordingYear, s.TempoBPM, s.ISRC, m.IsActive,
                GROUP_CONCAT(DISTINCT an.DisplayName) FILTER (WHERE r.RoleName = 'Performer') AS DisplayArtist,
                MIN(t.TagName) FILTER (WHERE t.TagCategory = 'Genre' AND mst.IsPrimary = 1) AS PrimaryGenre,
                EXISTS (SELECT 1 FROM RecordingPublishers rp WHERE rp.SourceID = m.SourceID) AS has_publisher,
                EXISTS (SELECT 1 FROM SongAlbums sa WHERE sa.SourceID = m.SourceID) AS has_album,
                COUNT(DISTINCT sc.CreditID) FILTER (WHERE r.RoleName = 'Performer') > 0 AS has_performer,
                COUNT(DISTINCT sc.CreditID) FILTER (WHERE r.RoleName = 'Composer') > 0 AS has_composer
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
        if conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, ids).fetchall()
            return [dict(row) for row in rows]

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            rows = new_conn.execute(query_sql, ids).fetchall()
            logger.debug(f"[SongRepository] <- search_slim_by_ids() found {len(rows)}")
            return [dict(row) for row in rows]

    def get_by_identity_ids(
        self,
        identity_ids: List[int],
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Song]:
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

        if conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, identity_ids).fetchall()
            return [self._row_to_song(row) for row in rows]

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            rows = new_conn.execute(query_sql, identity_ids).fetchall()
            return [self._row_to_song(row) for row in rows]

    def get_by_hash(
        self, audio_hash: str, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[Song]:
        """Fetch a Song by its audio-only hash using a single JOIN."""
        logger.debug(f"[SongRepository] -> get_by_hash(hash='{audio_hash}')")
        query = f"SELECT {self._COLUMNS} {self._JOIN} WHERE m.AudioHash = ?"

        if conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(query, (audio_hash,)).fetchone()
            return self._row_to_song(row) if row else None

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            row = new_conn.execute(query, (audio_hash,)).fetchone()
            return self._row_to_song(row) if row else None

    def get_by_processing_status(self, status: int) -> List["Song"]:
        """Fetch all non-deleted songs with a given processing status."""
        query = f"SELECT {self._COLUMNS} {self._JOIN} WHERE m.ProcessingStatus = ?"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, (status,)).fetchall()
            return [self._row_to_song(row) for row in rows if row]

    def get_by_path(
        self, path: str, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[Song]:
        """Fetch a song by its absolute source path using a single JOIN."""
        if not path:
            return None

        logger.debug(f"[SongRepository] -> get_by_path(path='{path}')")
        query = f"SELECT {self._COLUMNS} {self._JOIN} WHERE m.SourcePath = ?"

        if conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(query, (path,)).fetchone()
            return self._row_to_song(row) if row else None

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            row = new_conn.execute(query, (path,)).fetchone()
            return self._row_to_song(row) if row else None

    def find_by_metadata(
        self,
        title: str,
        artists: List[str],
        year: Optional[int],
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Song]:
        """
        Find songs matching Title, exact Performer set, and Recording Year.
        """
        if not title or not artists:
            return []

        logger.debug(
            f"[SongRepository] -> find_by_metadata(title='{title}', artists={artists}, year={year})"
        )

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

        def fetch_performers(connection, c_ids):
            p_placeholders = ",".join(["?" for _ in c_ids])
            performer_sql = f"""
                SELECT sc.SourceID, an.DisplayName 
                FROM SongCredits sc
                JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
                WHERE sc.SourceID IN ({p_placeholders})
                  AND sc.RoleID = (SELECT RoleID FROM Roles WHERE RoleName = 'Performer')
                  AND an.IsDeleted = 0
            """
            return connection.execute(performer_sql, c_ids).fetchall()

        if conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, tuple(params)).fetchall()
            candidates = [self._row_to_song(row) for row in rows]
            if not candidates:
                return []
            candidate_ids = [c.id for c in candidates if c.id is not None]
            p_rows = fetch_performers(conn, candidate_ids)
            source_performers: Dict[int, List[str]] = {}
            for r in p_rows:
                source_performers.setdefault(r["SourceID"], []).append(r["DisplayName"])
        else:
            with self._get_connection() as new_conn:
                new_conn.row_factory = sqlite3.Row
                rows = new_conn.execute(query_sql, tuple(params)).fetchall()
                candidates = [self._row_to_song(row) for row in rows]
                if not candidates:
                    return []
                candidate_ids = [c.id for c in candidates if c.id is not None]
                p_rows = fetch_performers(new_conn, candidate_ids)
                source_performers: Dict[int, List[str]] = {}
                for r in p_rows:
                    source_performers.setdefault(r["SourceID"], []).append(
                        r["DisplayName"]
                    )

        # Compare sets
        found_matches = []
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

    def get_filter_values(self, conn: Optional[sqlite3.Connection] = None) -> dict:
        """
        Returns all distinct values for each filter category.
        Used to populate the filter sidebar on app load or after a DB write.
        """
        queries = {
            "artists": """
                SELECT DISTINCT an.DisplayName AS val
                FROM ArtistNames an
                JOIN SongCredits sc ON an.NameID = sc.CreditedNameID
                JOIN Roles r ON sc.RoleID = r.RoleID
                JOIN MediaSources m ON sc.SourceID = m.SourceID
                WHERE r.RoleName = 'Performer' AND an.IsDeleted = 0 AND m.IsDeleted = 0
                ORDER BY an.DisplayName
            """,
            "contributors": """
                SELECT DISTINCT an.DisplayName AS val
                FROM ArtistNames an
                JOIN SongCredits sc ON an.NameID = sc.CreditedNameID
                JOIN MediaSources m ON sc.SourceID = m.SourceID
                WHERE an.IsDeleted = 0 AND m.IsDeleted = 0
                ORDER BY an.DisplayName
            """,
            "years": """
                SELECT DISTINCT s.RecordingYear AS val
                FROM Songs s
                JOIN MediaSources m ON s.SourceID = m.SourceID
                WHERE s.RecordingYear IS NOT NULL AND m.IsDeleted = 0
                ORDER BY s.RecordingYear DESC
            """,
            "decades": """
                SELECT DISTINCT (s.RecordingYear / 10) * 10 AS val
                FROM Songs s
                JOIN MediaSources m ON s.SourceID = m.SourceID
                WHERE s.RecordingYear IS NOT NULL AND m.IsDeleted = 0
                ORDER BY val DESC
            """,
            "genres": """
                SELECT DISTINCT t.TagName AS val
                FROM Tags t
                JOIN MediaSourceTags mst ON t.TagID = mst.TagID
                JOIN MediaSources m ON mst.SourceID = m.SourceID
                WHERE t.TagCategory = 'Genre' AND t.IsDeleted = 0 AND m.IsDeleted = 0
                ORDER BY t.TagName
            """,
            "albums": """
                SELECT DISTINCT a.AlbumTitle AS val
                FROM Albums a
                JOIN SongAlbums sa ON a.AlbumID = sa.AlbumID
                JOIN MediaSources m ON sa.SourceID = m.SourceID
                WHERE a.IsDeleted = 0 AND m.IsDeleted = 0
                ORDER BY a.AlbumTitle
            """,
            "publishers": """
                SELECT DISTINCT p.PublisherName AS val
                FROM Publishers p
                JOIN RecordingPublishers rp ON p.PublisherID = rp.PublisherID
                JOIN MediaSources m ON rp.SourceID = m.SourceID
                WHERE p.IsDeleted = 0 AND m.IsDeleted = 0
                ORDER BY p.PublisherName
            """,
        }

        def _run(c):
            c.row_factory = sqlite3.Row
            result = {
                key: [row["val"] for row in c.execute(sql).fetchall()]
                for key, sql in queries.items()
            }
            # Dynamic tag categories (all except Genre, which is promoted above)
            other_tags_rows = c.execute("""
                SELECT DISTINCT t.TagCategory AS cat, t.TagName AS val
                FROM Tags t
                JOIN MediaSourceTags mst ON t.TagID = mst.TagID
                JOIN MediaSources m ON mst.SourceID = m.SourceID
                WHERE t.TagCategory IS NOT NULL
                  AND LOWER(t.TagCategory) != 'genre'
                  AND t.IsDeleted = 0 AND m.IsDeleted = 0
                ORDER BY t.TagCategory, t.TagName
            """).fetchall()
            tag_categories: Dict[str, List[str]] = {}
            for row in other_tags_rows:
                tag_categories.setdefault(row["cat"], []).append(row["val"])
            result["tag_categories"] = tag_categories
            return result

        if conn:
            return _run(conn)
        with self._get_connection() as new_conn:
            return _run(new_conn)

    def filter_slim(
        self,
        artists: Optional[List[str]] = None,
        contributors: Optional[List[str]] = None,
        years: Optional[List[int]] = None,
        decades: Optional[List[int]] = None,
        genres: Optional[List[str]] = None,
        albums: Optional[List[str]] = None,
        publishers: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        live_only: bool = False,
        mode: str = "ALL",
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[dict]:
        """
        Returns slim song rows matching the given filter criteria.
        mode='ALL' = AND logic (intersection), mode='ANY' = OR logic (union).
        statuses: list of 'not_done', 'ready_to_finalize', 'missing_data', 'done'
        """
        logger.debug(f"[SongRepository] -> filter_slim(mode={mode})")

        subqueries: List[str] = []
        params: List[Any] = []
        is_all = mode.upper() == "ALL"

        def _add(sq: str, vals: List[Any]):
            subqueries.append(sq)
            params.extend(vals)

        def _add_standard_filter(values: Optional[List[Any]], base_sq: str, col: str):
            if not values:
                return
            if is_all:
                for v in values:
                    _add(f"{base_sq} AND {col} = ?", [v])
            else:
                ph = ",".join(["?"] * len(values))
                _add(f"{base_sq} AND {col} IN ({ph})", values)

        # 1. Standard matching fields
        _add_standard_filter(
            artists,
            "SELECT sc.SourceID FROM SongCredits sc JOIN ArtistNames an ON sc.CreditedNameID = an.NameID JOIN Roles r ON sc.RoleID = r.RoleID WHERE an.IsDeleted = 0 AND r.RoleName = 'Performer'",
            "an.DisplayName",
        )
        _add_standard_filter(
            contributors,
            "SELECT sc.SourceID FROM SongCredits sc JOIN ArtistNames an ON sc.CreditedNameID = an.NameID WHERE an.IsDeleted = 0",
            "an.DisplayName",
        )
        _add_standard_filter(
            years,
            "SELECT s.SourceID FROM Songs s WHERE 1=1",
            "s.RecordingYear",
        )
        _add_standard_filter(
            genres,
            "SELECT mst.SourceID FROM MediaSourceTags mst JOIN Tags t ON mst.TagID = t.TagID WHERE t.TagCategory = 'Genre' AND t.IsDeleted = 0",
            "t.TagName",
        )
        _add_standard_filter(
            albums,
            "SELECT sa.SourceID FROM SongAlbums sa JOIN Albums a ON sa.AlbumID = a.AlbumID WHERE a.IsDeleted = 0",
            "a.AlbumTitle",
        )
        _add_standard_filter(
            publishers,
            "SELECT rp.SourceID FROM RecordingPublishers rp JOIN Publishers p ON rp.PublisherID = p.PublisherID WHERE p.IsDeleted = 0",
            "p.PublisherName",
        )

        # 2. Decades
        if decades:
            base = "SELECT s.SourceID FROM Songs s WHERE"
            if is_all:
                for d in decades:
                    _add(
                        f"{base} s.RecordingYear >= ? AND s.RecordingYear < ?",
                        [d, d + 10],
                    )
            else:
                clauses = " OR ".join(
                    ["(s.RecordingYear >= ? AND s.RecordingYear < ?)"] * len(decades)
                )
                _add(f"{base} {clauses}", [val for d in decades for val in (d, d + 10)])

        # 3. Tags (category:value)
        if tags:
            parsed = [t.split(":", 1) for t in tags if ":" in t]
            if parsed:
                base = "SELECT mst.SourceID FROM MediaSourceTags mst JOIN Tags t ON mst.TagID = t.TagID WHERE t.IsDeleted = 0 AND"
                if is_all:
                    for cat, val in parsed:
                        _add(f"{base} t.TagName = ? AND t.TagCategory = ?", [val, cat])
                else:
                    clauses = " OR ".join(
                        ["(t.TagName = ? AND t.TagCategory = ?)"] * len(parsed)
                    )
                    _add(
                        f"{base} ({clauses})",
                        [v for pair in parsed for v in (pair[1], pair[0])],
                    )

        # 4. Statuses
        if statuses:
            status_map = {
                "done": f"m.ProcessingStatus = {ProcessingStatus.REVIEWED}",
                "not_done": f"m.ProcessingStatus != {ProcessingStatus.REVIEWED}",
                "missing_data": f"m.ProcessingStatus != {ProcessingStatus.REVIEWED} AND ({BLOCKER_SQL})",
                "ready_to_finalize": f"m.ProcessingStatus != {ProcessingStatus.REVIEWED} AND {NO_BLOCKER_SQL}",
            }
            parts = [
                f"SELECT m.SourceID FROM MediaSources m LEFT JOIN Songs s ON m.SourceID = s.SourceID WHERE m.IsDeleted = 0 AND {status_map[s]}"
                for s in statuses
                if s in status_map
            ]
            if parts:
                subqueries.append(" UNION ".join(parts))

        if not subqueries:
            id_filter = "1=1"
        elif mode.upper() == "ANY":
            id_filter = "m.SourceID IN (" + " UNION ".join(subqueries) + ")"
        else:  # ALL (default)
            id_filter = " AND ".join([f"m.SourceID IN ({sq})" for sq in subqueries])

        live_clause = "AND m.IsActive = 1" if live_only else ""

        query_sql = f"""
            SELECT
                m.SourceID, m.MediaName, m.SourcePath, m.SourceDuration, m.ProcessingStatus,
                s.RecordingYear, s.TempoBPM, s.ISRC, m.IsActive,
                GROUP_CONCAT(DISTINCT an.DisplayName) FILTER (WHERE r.RoleName = 'Performer') AS DisplayArtist,
                MIN(t.TagName) FILTER (WHERE t.TagCategory = 'Genre' AND mst.IsPrimary = 1) AS PrimaryGenre,
                EXISTS (SELECT 1 FROM RecordingPublishers rp WHERE rp.SourceID = m.SourceID) AS has_publisher,
                EXISTS (SELECT 1 FROM SongAlbums sa WHERE sa.SourceID = m.SourceID) AS has_album,
                COUNT(DISTINCT sc.CreditID) FILTER (WHERE r.RoleName = 'Performer') > 0 AS has_performer,
                COUNT(DISTINCT sc.CreditID) FILTER (WHERE r.RoleName = 'Composer') > 0 AS has_composer
            FROM MediaSources m
            JOIN Songs s ON m.SourceID = s.SourceID
                AND m.TypeID = (SELECT TypeID FROM Types WHERE TypeName = 'Song')
                AND m.IsDeleted = 0
            LEFT JOIN SongCredits sc ON m.SourceID = sc.SourceID
            LEFT JOIN ArtistNames an ON sc.CreditedNameID = an.NameID AND an.IsDeleted = 0
            LEFT JOIN Roles r ON sc.RoleID = r.RoleID
            LEFT JOIN MediaSourceTags mst ON m.SourceID = mst.SourceID
            LEFT JOIN Tags t ON mst.TagID = t.TagID AND t.IsDeleted = 0
            WHERE {id_filter} {live_clause}
            GROUP BY m.SourceID
        """

        def _run(c):
            c.row_factory = sqlite3.Row
            rows = c.execute(query_sql, params).fetchall()
            logger.debug(f"[SongRepository] <- filter_slim() found {len(rows)}")
            return [dict(row) for row in rows]

        if conn:
            return _run(conn)
        with self._get_connection() as new_conn:
            return _run(new_conn)

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
            estimated_original_path=row["OriginPath"],
        )
