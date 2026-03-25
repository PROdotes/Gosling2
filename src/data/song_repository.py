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
    _JOIN = "FROM MediaSources m JOIN Songs s ON m.SourceID = s.SourceID AND m.TypeID = (SELECT TypeID FROM Types WHERE TypeName = 'Song')"

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

    def search_surface(self, query: str) -> List[Song]:
        """Discovery path on titles and albums. Fastest search."""
        logger.debug(f"[SongRepository] -> search_surface(query='{query}')")
        fmt_q = f"%{query}%"
        query_sql = f"""
            SELECT {self._COLUMNS} {self._JOIN}
            WHERE m.MediaName LIKE ?
               OR m.SourceID IN (
                   SELECT sa.SourceID FROM SongAlbums sa
                   JOIN Albums a ON sa.AlbumID = a.AlbumID
                   WHERE a.AlbumTitle LIKE ?
               )
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query_sql, (fmt_q, fmt_q)).fetchall()
            logger.debug(
                f"[SongRepository] <- search_surface(query='{query}') found {len(rows)}"
            )
            return [self._row_to_song(row) for row in rows]

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
                WHERE an.OwnerIdentityID IN ({placeholders})
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
