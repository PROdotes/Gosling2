import sqlite3
from typing import List, Optional, Dict, Mapping, Any

from src.data.base_repository import BaseRepository
from src.models.domain import Album
from src.services.logger import logger


class AlbumRepository(BaseRepository):
    """Repository for loading first-class Album records."""

    _COLUMNS = "AlbumID, AlbumTitle, AlbumType, ReleaseYear"

    def get_all(self, conn: Optional[sqlite3.Connection] = None) -> List[Album]:
        """Fetch the full album directory."""
        logger.debug("[AlbumRepository] -> get_all()")
        query = f"SELECT {self._COLUMNS} FROM Albums WHERE IsDeleted = 0 ORDER BY AlbumTitle COLLATE NOCASE ASC"

        if conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
            return [self._row_to_album(row) for row in rows]

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            rows = new_conn.execute(query).fetchall()
            result = [self._row_to_album(row) for row in rows]
            logger.debug(f"[AlbumRepository] <- get_all() count={len(result)}")
            return result

    def search_slim(
        self, query: str, conn: Optional[sqlite3.Connection] = None
    ) -> List[dict]:
        """Fast list-view query. Returns dicts for AlbumSlimView — no tracklist hydration."""
        logger.debug(f"[AlbumRepository] -> search_slim(q='{query}')")
        sql = """
            SELECT
                a.AlbumID, a.AlbumTitle, a.AlbumType, a.ReleaseYear,
                GROUP_CONCAT(DISTINCT an.DisplayName) FILTER (WHERE r.RoleName = 'Performer') AS DisplayArtist,
                MIN(p.PublisherName) AS DisplayPublisher,
                (SELECT COUNT(*) FROM SongAlbums sa WHERE sa.AlbumID = a.AlbumID) AS SongCount
            FROM Albums a
            LEFT JOIN AlbumCredits ac ON a.AlbumID = ac.AlbumID
            LEFT JOIN ArtistNames an ON ac.CreditedNameID = an.NameID AND an.IsDeleted = 0
            LEFT JOIN Roles r ON ac.RoleID = r.RoleID
            LEFT JOIN AlbumPublishers ap ON a.AlbumID = ap.AlbumID
            LEFT JOIN Publishers p ON ap.PublisherID = p.PublisherID AND p.IsDeleted = 0
            WHERE a.AlbumTitle LIKE ? AND a.IsDeleted = 0
            GROUP BY a.AlbumID
            ORDER BY a.AlbumTitle COLLATE NOCASE ASC
        """
        if conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, (f"%{query}%",)).fetchall()
            return [dict(row) for row in rows]

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            rows = new_conn.execute(sql, (f"%{query}%",)).fetchall()
            result = [dict(row) for row in rows]
            logger.debug(
                f"[AlbumRepository] <- search_slim(q='{query}') count={len(result)}"
            )
            return result

    def get_by_id(
        self, album_id: int, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[Album]:
        """Fetch a single album by ID."""
        logger.debug(f"[AlbumRepository] -> get_by_id(id={album_id})")
        query = (
            f"SELECT {self._COLUMNS} FROM Albums WHERE AlbumID = ? AND IsDeleted = 0"
        )
        if conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(query, (album_id,)).fetchone()
            if row is None:
                return None
            return self._row_to_album(row)

        with self._get_connection() as new_conn:
            new_conn.row_factory = sqlite3.Row
            row = new_conn.execute(query, (album_id,)).fetchone()
            if row is None:
                logger.warning(
                    f"[AlbumRepository] <- get_by_id(id={album_id}) NOT_FOUND"
                )
                return None
            result = self._row_to_album(row)
            logger.debug(
                f"[AlbumRepository] <- get_by_id(id={album_id}) '{result.title}'"
            )
            return result

    def get_song_ids_by_album(
        self, album_id: int, conn: Optional[sqlite3.Connection] = None
    ) -> List[int]:
        """Fetch all song IDs linked to an album."""
        logger.debug(f"[AlbumRepository] -> get_song_ids_by_album(id={album_id})")
        return self.get_song_ids_for_albums([album_id], conn).get(album_id, [])

    def get_song_ids_for_albums(
        self, album_ids: List[int], conn: Optional[sqlite3.Connection] = None
    ) -> Dict[int, List[int]]:
        """Batch fetch song IDs for a set of albums in a single query."""
        if not album_ids:
            return {}

        logger.debug(
            f"[AlbumRepository] -> get_song_ids_for_albums(count={len(album_ids)})"
        )
        placeholders = ",".join(["?"] * len(album_ids))
        query = f"""
            SELECT sa.AlbumID, sa.SourceID
            FROM SongAlbums sa
            JOIN MediaSources ms ON sa.SourceID = ms.SourceID
            WHERE sa.AlbumID IN ({placeholders}) AND ms.IsDeleted = 0
            ORDER BY sa.DiscNumber, sa.TrackNumber, sa.SourceID
        """

        results: Dict[int, List[int]] = {}
        if conn:
            rows = conn.execute(query, album_ids).fetchall()
            for album_id, song_id in rows:
                results.setdefault(album_id, []).append(song_id)
            return results

        with self._get_connection() as new_conn:
            rows = new_conn.execute(query, album_ids).fetchall()
            for album_id, song_id in rows:
                results.setdefault(album_id, []).append(song_id)

            logger.debug(
                f"[AlbumRepository] <- get_song_ids_for_albums() grouped={len(results)} albums"
            )
            return results

    def create_album(
        self,
        title: str,
        album_type: Optional[str],
        release_year: Optional[int],
        conn: sqlite3.Connection,
    ) -> int:
        """
        Get-or-create an Album by title+year. Reactivates soft-deleted. Returns album_id. Does NOT commit.
        """
        logger.debug(
            f"[AlbumRepository] -> create_album(title='{title}', year={release_year})"
        )
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT AlbumID, IsDeleted FROM Albums WHERE AlbumTitle = ? COLLATE UTF8_NOCASE AND ReleaseYear IS ?",
            (title, release_year),
        ).fetchone()
        if row:
            album_id = row[0]
            if row[1]:
                cursor.execute(
                    "UPDATE Albums SET IsDeleted = 0 WHERE AlbumID = ?", (album_id,)
                )
            logger.debug(
                f"[AlbumRepository] <- create_album() reused album_id={album_id}"
            )
            return album_id
        cursor.execute(
            "INSERT INTO Albums (AlbumTitle, AlbumType, ReleaseYear) VALUES (?, ?, ?)",
            (title, album_type, release_year),
        )
        album_id = cursor.lastrowid
        logger.debug(f"[AlbumRepository] <- create_album() created album_id={album_id}")
        return album_id

    def update_album(
        self, album_id: int, fields: dict, conn: sqlite3.Connection
    ) -> None:
        """
        Update editable Album fields. Partial updates — only send changed fields.
        Does NOT commit.
        """
        logger.debug(
            f"[AlbumRepository] -> update_album(album_id={album_id}, fields={list(fields.keys())})"
        )
        col_map = {
            "title": "AlbumTitle",
            "album_type": "AlbumType",
            "release_year": "ReleaseYear",
        }
        valid = {k: v for k, v in fields.items() if k in col_map}
        if not valid:
            return
        set_clause = ", ".join(f"{col_map[k]} = ?" for k in valid)
        conn.cursor().execute(
            f"UPDATE Albums SET {set_clause} WHERE AlbumID = ?",
            (*valid.values(), album_id),
        )
        logger.debug("[AlbumRepository] <- update_album() done")

    def soft_delete(self, album_id: int, conn: sqlite3.Connection) -> bool:
        """Set IsDeleted = 1 for an album. Returns True if a record was updated."""
        logger.debug(f"[AlbumRepository] -> soft_delete(id={album_id})")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Albums SET IsDeleted = 1 WHERE AlbumID = ? AND IsDeleted = 0",
            (album_id,),
        )
        updated = cursor.rowcount > 0
        logger.debug(f"[AlbumRepository] <- soft_delete(id={album_id}) updated={updated}")
        return updated

    def delete_album_links(self, album_id: int, conn: sqlite3.Connection) -> None:
        """Hard-delete AlbumCredits and AlbumPublishers rows for this album. Does NOT commit."""
        logger.debug(f"[AlbumRepository] -> delete_album_links(id={album_id})")
        conn.execute("DELETE FROM AlbumCredits WHERE AlbumID = ?", (album_id,))
        conn.execute("DELETE FROM AlbumPublishers WHERE AlbumID = ?", (album_id,))
        logger.debug(f"[AlbumRepository] <- delete_album_links(id={album_id}) done")

    def _row_to_album(self, row: Mapping[str, Any]) -> Album:
        return Album(
            id=row["AlbumID"],
            title=row["AlbumTitle"],
            album_type=row["AlbumType"],
            release_year=row["ReleaseYear"],
        )
