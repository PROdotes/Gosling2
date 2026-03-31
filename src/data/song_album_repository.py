import sqlite3
from typing import Any, List, Mapping, Optional
from src.data.base_repository import BaseRepository
from src.data.song_credit_repository import SongCreditRepository
from src.models.domain import SongAlbum
from src.services.logger import logger


class SongAlbumRepository(BaseRepository):
    """Repository for loading Album associations for Songs."""

    _QUERY = """
        SELECT sa.SourceID, sa.AlbumID, sa.TrackNumber, sa.DiscNumber, sa.IsPrimary,
               a.AlbumTitle, a.AlbumType, a.ReleaseYear
        FROM SongAlbums sa
        JOIN Albums a ON sa.AlbumID = a.AlbumID
        WHERE sa.SourceID IN ({placeholders})
    """

    def get_albums_for_songs(self, song_ids: List[int]) -> List[SongAlbum]:
        """Batch-fetch album associations for multiple songs."""
        if not song_ids:
            return []

        logger.debug(
            f"[SongAlbumRepository] Batch-fetching albums for {len(song_ids)} songs."
        )
        placeholders = ",".join(["?" for _ in song_ids])
        query = self._QUERY.format(placeholders=placeholders)

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, song_ids).fetchall()
            logger.debug(f"[SongAlbumRepository] Found {len(rows)} album associations.")
            return [self._row_to_song_album(row) for row in rows]

    def get_albums_for_songs_reverse(self, album_ids: List[int]) -> List[SongAlbum]:
        """Reverse Batch-fetch: Find all song associations for a set of albums."""
        if not album_ids:
            return []

        logger.debug(
            f"[SongAlbumRepository] Batch-fetching songs for {len(album_ids)} albums."
        )
        placeholders = ",".join(["?" for _ in album_ids])
        # We reuse the same base query but filter by AlbumID instead of SourceID
        query = self._QUERY.replace(
            "sa.SourceID IN ({placeholders})", f"sa.AlbumID IN ({placeholders})"
        )
        query = query.format(placeholders=placeholders)

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, album_ids).fetchall()
            logger.debug(f"[SongAlbumRepository] Found {len(rows)} song associations.")
            return [self._row_to_song_album(row) for row in rows]

    def insert_albums(
        self, source_id: int, albums: List[SongAlbum], conn: sqlite3.Connection
    ) -> None:
        """Get-or-create Albums rows (by Title+Year+Artist), then insert SongAlbums links."""
        logger.debug(
            f"[SongAlbumRepository] -> insert_albums(source_id={source_id}, count={len(albums)})"
        )
        if not albums:
            logger.debug("[SongAlbumRepository] <- insert_albums() empty list, no-op")
            return

        cursor = conn.cursor()
        for album in albums:
            album_id, was_deleted = self._find_matching_album(cursor, album)

            if album_id is None:
                cursor.execute(
                    "INSERT INTO Albums (AlbumTitle, AlbumType, ReleaseYear) VALUES (?, ?, ?)",
                    (album.album_title, album.album_type, album.release_year),
                )
                album_id = cursor.lastrowid
                assert isinstance(
                    album_id, int
                ), "Failed to retrieve AlbumID after insert"
                self._insert_album_credits(cursor, album_id, album)
            elif was_deleted:
                # Reconnect soft-deleted album
                cursor.execute(
                    "UPDATE Albums SET IsDeleted = 0 WHERE AlbumID = ?", (album_id,)
                )

            # Insert link
            cursor.execute(
                "INSERT INTO SongAlbums (SourceID, AlbumID, TrackNumber, DiscNumber, IsPrimary) VALUES (?, ?, ?, ?, ?)",
                (
                    source_id,
                    album_id,
                    album.track_number,
                    album.disc_number,
                    1 if album.is_primary else 0,
                ),
            )

        logger.info(
            f"[SongAlbumRepository] <- insert_albums(source_id={source_id}) wrote {len(albums)} albums"
        )

    def _find_matching_album(self, cursor, album: SongAlbum):
        """Find an existing album matching Title+Year+Artist. Returns AlbumID or None.
        Includes soft-deleted albums — caller handles reconnection."""
        logger.debug(
            f"[SongAlbumRepository] -> _find_matching_album(title='{album.album_title}', year={album.release_year})"
        )
        rows = cursor.execute(
            "SELECT AlbumID, IsDeleted FROM Albums WHERE AlbumTitle = ? COLLATE UTF8_NOCASE AND ReleaseYear IS ?",
            (album.album_title, album.release_year),
        ).fetchall()

        if not rows:
            logger.debug(
                "[SongAlbumRepository] <- _find_matching_album() no title+year candidates"
            )
            return None, False

        incoming_artists = sorted(c.display_name.lower() for c in album.credits)

        # No credits on the incoming album — fall back to Title+Year only
        if not incoming_artists:
            logger.debug(
                f"[SongAlbumRepository] <- _find_matching_album() no incoming credits, reusing AlbumID={rows[0][0]}"
            )
            return rows[0][0], bool(rows[0][1])

        for row in rows:
            candidate_id = row[0]
            existing_artists = sorted(
                r[0].lower()
                for r in cursor.execute(
                    "SELECT an.DisplayName FROM AlbumCredits ac "
                    "JOIN ArtistNames an ON ac.CreditedNameID = an.NameID "
                    "WHERE ac.AlbumID = ?",
                    (candidate_id,),
                ).fetchall()
            )
            if existing_artists == incoming_artists:
                logger.debug(
                    f"[SongAlbumRepository] <- _find_matching_album() artist match, reusing AlbumID={candidate_id}"
                )
                return candidate_id, bool(row[1])
            # Also match if the existing album has no credits yet
            if not existing_artists:
                logger.debug(
                    f"[SongAlbumRepository] <- _find_matching_album() existing has no credits, reusing AlbumID={candidate_id}"
                )
                return candidate_id, bool(row[1])

        logger.debug(
            "[SongAlbumRepository] <- _find_matching_album() no artist match, will create new"
        )
        return None, False

    def _insert_album_credits(self, cursor, album_id: int, album: SongAlbum) -> None:
        """Write AlbumCredits rows for a newly created album."""
        if not album.credits:
            return
        logger.debug(
            f"[SongAlbumRepository] -> _insert_album_credits(album_id={album_id}, count={len(album.credits)})"
        )
        credit_repo = SongCreditRepository(self.db_path)
        for credit in album.credits:
            role_id = credit_repo.get_or_create_role(credit.role_name, cursor)
            name_id = credit_repo.get_or_create_credit_name(credit.display_name, cursor)
            cursor.execute(
                "INSERT INTO AlbumCredits (AlbumID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
                (album_id, name_id, role_id),
            )
        logger.debug(
            f"[SongAlbumRepository] <- _insert_album_credits(album_id={album_id}) wrote {len(album.credits)} credits"
        )

    def add_album(
        self,
        source_id: int,
        album_id: int,
        track_number: int,
        disc_number: int,
        conn: sqlite3.Connection,
    ) -> None:
        """
        Link a song to an existing album. Does NOT commit.
        """
        logger.debug(
            f"[SongAlbumRepository] -> add_album(source_id={source_id}, album_id={album_id})"
        )
        conn.cursor().execute(
            "INSERT OR IGNORE INTO SongAlbums (SourceID, AlbumID, TrackNumber, DiscNumber, IsPrimary) VALUES (?, ?, ?, ?, 1)",
            (source_id, album_id, track_number, disc_number),
        )
        logger.debug("[SongAlbumRepository] <- add_album() done")

    def remove_album(
        self, source_id: int, album_id: int, conn: sqlite3.Connection
    ) -> None:
        """
        Remove a song-album link. Keeps Album record. Does NOT commit.
        """
        logger.debug(
            f"[SongAlbumRepository] -> remove_album(source_id={source_id}, album_id={album_id})"
        )
        conn.cursor().execute(
            "DELETE FROM SongAlbums WHERE SourceID = ? AND AlbumID = ?",
            (source_id, album_id),
        )
        logger.debug("[SongAlbumRepository] <- remove_album() done")

    def update_track_info(
        self,
        source_id: int,
        album_id: int,
        track_number: Optional[int],
        disc_number: Optional[int],
        conn: sqlite3.Connection,
    ) -> None:
        """
        Update track/disc number for a song-album link. Partial updates supported.
        """
        logger.debug(
            f"[SongAlbumRepository] -> update_track_info(id={source_id}, album_id={album_id})"
        )

        updates = []
        params = []
        if track_number is not None:
            updates.append("TrackNumber = ?")
            params.append(track_number)
        if disc_number is not None:
            updates.append("DiscNumber = ?")
            params.append(disc_number)

        if not updates:
            logger.debug("[SongAlbumRepository] <- update_track_info() no-op")
            return

        params.extend([source_id, album_id])
        sql = f"UPDATE SongAlbums SET {', '.join(updates)} WHERE SourceID = ? AND AlbumID = ?"
        conn.cursor().execute(sql, params)
        logger.debug("[SongAlbumRepository] <- update_track_info() done")

    def _row_to_song_album(self, row: Mapping[str, Any]) -> SongAlbum:
        """Map a database row to a SongAlbum Pydantic model."""
        return SongAlbum(
            source_id=row["SourceID"],
            album_id=row["AlbumID"],
            track_number=row["TrackNumber"],
            disc_number=row["DiscNumber"],
            is_primary=bool(row["IsPrimary"]),
            album_title=row["AlbumTitle"],
            album_type=row["AlbumType"],
            release_year=row["ReleaseYear"],
            album_publishers=[],  # Hydrated later by CatalogService
        )
