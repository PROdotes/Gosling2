"""
Song Sync Service
Handles complex many-to-many relationship synchronization for Song metadata.
Moved from SongRepository to improve maintainability and follow SOA.
"""
import os
from typing import Optional, List, Any, Set
import sqlite3
from src.data.models.song import Song
from src.core.audit_logger import AuditLogger
from src.core import logger

class SongSyncService:
    """Service for synchronizing song relationships (Contributors, Albums, Publishers, Tags)."""

    def __init__(self, contributor_repository=None):
        # We might need a contributor_repository for identity resolution
        # But for now we can use the cursor passed in
        self._contributor_repo = contributor_repository

    def sync_all(self, song: Song, cursor: sqlite3.Cursor, auditor: Optional[AuditLogger] = None, album_type: Optional[str] = None) -> None:
        """Sync all relationships for a song."""
        self.sync_contributor_roles(song, cursor, auditor)
        if song.album is not None:
            self.sync_album(song, cursor, auditor, album_type=album_type)
        if song.publisher is not None:
            self.sync_publisher(song, cursor, auditor)
        self.sync_tags(song, cursor, auditor)

    def sync_contributor_roles(self, song: Song, cursor: sqlite3.Cursor, auditor: Optional[AuditLogger] = None) -> None:
        """Sync contributors by calculating diff between DB and Object model."""
        conn = cursor.connection
        
        # 1. Calculate Desired State
        role_map = {
            'performers': 'Performer',
            'composers': 'Composer',
            'lyricists': 'Lyricist',
            'producers': 'Producer'
        }
        
        # V2 Goals (SongCredits -> ArtistNames)
        desired_links = set() # Set of (NameID, RoleID)
        
        for attr, role_name in role_map.items():
            contributors = getattr(song, attr, [])
            if not contributors: continue

             # Get RoleID
            cursor.execute("SELECT RoleID FROM Roles WHERE RoleName = ?", (role_name,))
            role_row = cursor.fetchone()
            if not role_row: continue
            role_id = role_row[0]

            for contributor_name in contributors:
                if not contributor_name.strip(): continue

                # Resolve to ArtistNames (V2)
                name_id = self._resolve_identity(cursor, contributor_name, auditor)
                desired_links.add((name_id, role_id))

        # 2. Get Current State (V2)
        cursor.execute("SELECT CreditedNameID, RoleID FROM SongCredits WHERE SourceID = ?", (song.source_id,))
        current_links_raw = cursor.fetchall()
        current_links = set((n, r) for n, r in current_links_raw)
            
        # 3. Calculate Diff (V2)
        to_add = desired_links - current_links
        to_remove = current_links - desired_links
        
        # 4. Execute Changes (V2)
        # DELETE
        for n_id, r_id in to_remove:
            cursor.execute(
                "DELETE FROM SongCredits WHERE SourceID = ? AND CreditedNameID = ? AND RoleID = ?",
                (song.source_id, n_id, r_id)
            )
            if auditor:
                auditor.log_delete("SongCredits", f"{song.source_id}-{n_id}-{r_id}", {
                    "SourceID": song.source_id,
                    "CreditedNameID": n_id,
                    "RoleID": r_id
                })
                
        # INSERT
        for n_id, r_id in to_add:
            cursor.execute(
                "INSERT INTO SongCredits (SourceID, CreditedNameID, RoleID) VALUES (?, ?, ?)",
                (song.source_id, n_id, r_id)
            )
            if auditor:
                auditor.log_insert("SongCredits", f"{song.source_id}-{n_id}-{r_id}", {
                    "SourceID": song.source_id,
                    "CreditedNameID": n_id,
                    "RoleID": r_id
                })

    def _resolve_identity(self, cursor: sqlite3.Cursor, name: str, auditor: Optional[AuditLogger]) -> int:
        """Helper to resolve a name to a NameID."""
        # 1. Exact Match on DisplayName (case-insensitive)
        cursor.execute("SELECT NameID FROM ArtistNames WHERE DisplayName = ? COLLATE UTF8_NOCASE", (name,))
        row = cursor.fetchone()
        if row:
            return row[0]
            
        # 2. Create New Name (Orphan for now, as per recommendation in Proposal)
        cursor.execute("INSERT INTO ArtistNames (DisplayName, SortName, IsPrimaryName) VALUES (?, ?, 0)", (name, name))
        name_id = cursor.lastrowid
        if auditor:
            auditor.log_insert("ArtistNames", name_id, {"DisplayName": name, "SortName": name, "IsPrimaryName": 0})
        return name_id

    def sync_album(self, song: Song, cursor: sqlite3.Cursor, auditor: Optional[AuditLogger] = None, album_type: Optional[str] = None) -> None:
        """Sync album relationship (Find or Create with Artist Disambiguation)."""
        # 0. Normalize Inputs -> Determine Target IDs
        effective_title = None
        all_titles = []
        
        # Helper to filter garbage
        def is_valid_title(t):
            if not t: return False
            s = str(t).strip()
            return s and s.upper() != "N/A"

        if isinstance(song.album, list):
            all_titles = [str(t).strip() for t in song.album if is_valid_title(t)]
            effective_title = all_titles[0] if all_titles else ""
        elif song.album:
             t = str(song.album).strip()
             if is_valid_title(t):
                 all_titles = [t]
                 effective_title = t

        target_ids = []
        
        # A. Attempt Precise ID Match
        use_precise_id = False
        if getattr(song, 'album_id', None) is not None:
             if not effective_title:
                 use_precise_id = True
             else:
                 check_id = song.album_id
                 if isinstance(check_id, list): check_id = check_id[0] if check_id else None
                 cursor.execute("SELECT AlbumTitle FROM Albums WHERE AlbumID = ?", (check_id,))
                 id_row = cursor.fetchone()
                 if id_row and id_row[0].lower() == effective_title.lower():
                     use_precise_id = True

        if use_precise_id:
             ids = song.album_id
             if isinstance(ids, list): target_ids = ids
             elif ids: target_ids = [ids]
             
        elif all_titles:
            # B. Get/Create by Name
            album_artist = getattr(song, 'album_artist', None)
            if album_artist: album_artist = album_artist.strip() or None
            release_year = getattr(song, 'recording_year', None)
            
            for album_title in all_titles:
                # 1. Find candidates by Title + Year
                base_query = "SELECT AlbumID FROM Albums WHERE AlbumTitle = ? COLLATE UTF8_NOCASE"
                base_params = [album_title]
                if release_year:
                    base_query += " AND ReleaseYear = ?"
                    base_params.append(release_year)
                else:
                    base_query += " AND ReleaseYear IS NULL"
                
                cursor.execute(base_query, base_params)
                candidates = [row[0] for row in cursor.fetchall()]
                
                # 2. Verify Artist (M2M)
                found_id = None
                target_names = set()
                if album_artist:
                    if '|||' in album_artist:
                        target_names = {a.strip().lower() for a in album_artist.split('|||') if a.strip()}
                    else:
                        target_names = {a.strip().lower() for a in album_artist.split(',') if a.strip()}

                for cand_id in candidates:
                     cursor.execute("""
                        SELECT lower(AN.DisplayName) 
                        FROM AlbumCredits AC 
                        JOIN ArtistNames AN ON AC.CreditedNameID = AN.NameID 
                        WHERE AC.AlbumID = ?
                     """, (cand_id,))
                     linked_names = {row[0] for row in cursor.fetchall()}
                     
                     if linked_names == target_names:
                         found_id = cand_id
                         break
                
                if found_id:
                    target_ids.append(found_id)
                else:
                    # Create New
                    if album_type is None:
                        album_type = 'Album'
                        
                    cursor.execute("INSERT INTO Albums (AlbumTitle, AlbumType, ReleaseYear) VALUES (?, ?, ?)", (album_title, album_type, release_year))
                    new_album_id = cursor.lastrowid
                    target_ids.append(new_album_id)
                    if auditor:
                        auditor.log_insert("Albums", new_album_id, {"AlbumTitle": album_title, "AlbumArtist": album_artist, "AlbumType": album_type, "ReleaseYear": release_year})
                    
                    # T-91: Link Album Artist via M2M if artist provided
                    if album_artist:
                        if '|||' in album_artist:
                            artist_names = [a.strip() for a in album_artist.split('|||')]
                        else:
                            artist_names = [a.strip() for a in album_artist.split(',')]
                        for a_name in artist_names:
                            # Resolve Name to NameID
                            name_id = self._resolve_identity(cursor, a_name, auditor)

                            cursor.execute(
                                """
                                INSERT OR IGNORE INTO AlbumCredits (AlbumID, CreditedNameID, RoleID) 
                                VALUES (?, ?, (SELECT RoleID FROM Roles WHERE RoleName = 'Performer'))
                                """,
                                (new_album_id, name_id)
                            )
                            if cursor.rowcount > 0 and auditor:
                                auditor.log_insert("AlbumCredits", f"{new_album_id}-{name_id}", {"AlbumID": new_album_id, "CreditedNameID": name_id})

        # Handle 'Clear Album' scenario
        if effective_title is not None and not effective_title.strip() and not use_precise_id:
            target_ids = [] 
            
        cursor.execute("SELECT AlbumID, TrackNumber, IsPrimary FROM SongAlbums WHERE SourceID = ?", (song.source_id,))
        current_map = {r[0]: {'IsPrimary': r[2], 'TrackNumber': r[1]} for r in cursor.fetchall()}
            
        # Diff and Apply
        target_set = set(target_ids)
        current_set = set(current_map.keys())
        
        to_remove = current_set - target_set
        to_add = target_set - current_set
        
        for aid in to_remove:
            cursor.execute("DELETE FROM SongAlbums WHERE SourceID = ? AND AlbumID = ?", (song.source_id, aid))
            if auditor:
                auditor.log_delete("SongAlbums", f"{song.source_id}-{aid}", {"SourceID": song.source_id, "AlbumID": aid})
                
        for aid in to_add:
            # Default to IsPrimary=1 if it's the only one or if we have it in model?
            # For now simplified logic
            cursor.execute("INSERT INTO SongAlbums (SourceID, AlbumID, IsPrimary) VALUES (?, ?, 1)", (song.source_id, aid))
            if auditor:
                auditor.log_insert("SongAlbums", f"{song.source_id}-{aid}", {"SourceID": song.source_id, "AlbumID": aid, "IsPrimary": 1})

    def sync_publisher(self, song: Song, cursor: sqlite3.Cursor, auditor: Optional[AuditLogger] = None) -> None:
        """Sync publisher relationship (ID-based prioritized)."""
        desired_ids = set()
        publisher_ids_ordered = []

        # 1. Use Precise IDs if available (T-180)
        # Prioritize non-empty IDs; if IDs are empty but names are present, fall back to names
        p_ids = getattr(song, 'publisher_id', None)
        if p_ids:
            if isinstance(p_ids, list):
                publisher_ids_ordered = [int(pid) for pid in p_ids if pid]
            else:
                publisher_ids_ordered = [int(p_ids)]
            desired_ids = set(publisher_ids_ordered)
        
        # 2. Fallback to Name-based sync (Legacy/ID3 Tag driven / RESEED)
        elif song.publisher:
            if isinstance(song.publisher, list):
                publisher_names = [str(p).strip() for p in song.publisher if p]
            else:
                raw_val = song.publisher or ""
                if '|||' in raw_val:
                    publisher_names = [p.strip() for p in raw_val.split('|||') if p.strip()]
                else:
                    publisher_names = [p.strip() for p in raw_val.split(',') if p.strip()]

            from src.data.repositories.publisher_repository import PublisherRepository
            pub_repo = PublisherRepository()

            for pub_name in publisher_names:
                # T-Fix: Use Repository's get_or_create which handles whitespaces consistently (trim)
                publisher, _ = pub_repo.get_or_create(pub_name, conn=cursor.connection)
                pid = publisher.publisher_id
                
                desired_ids.add(pid)
                publisher_ids_ordered.append(pid)

        cursor.execute("SELECT PublisherID FROM RecordingPublishers WHERE SourceID = ?", (song.source_id,))
        current_ids = set(r[0] for r in cursor.fetchall())
        
        to_add = desired_ids - current_ids
        to_remove = current_ids - desired_ids
        
        for pid in to_remove:
            cursor.execute("DELETE FROM RecordingPublishers WHERE SourceID = ? AND PublisherID = ?", (song.source_id, pid))
            if auditor:
                auditor.log_delete("RecordingPublishers", f"{song.source_id}-{pid}", {"SourceID": song.source_id, "PublisherID": pid})
                
        for pid in to_add:
            cursor.execute("INSERT INTO RecordingPublishers (SourceID, PublisherID) VALUES (?, ?)", (song.source_id, pid))
            if auditor:
                auditor.log_insert("RecordingPublishers", f"{song.source_id}-{pid}", {"SourceID": song.source_id, "PublisherID": pid})

        # Track Overrides in SongAlbums
        cursor.execute("SELECT AlbumID FROM SongAlbums WHERE SourceID = ?", (song.source_id,))
        album_ids = [r[0] for r in cursor.fetchall()]
        
        if album_ids:
            primary_pid = publisher_ids_ordered[0] if publisher_ids_ordered else None
            if auditor:
                cursor.execute("SELECT AlbumID, TrackPublisherID FROM SongAlbums WHERE SourceID = ?", (song.source_id,))
                for a_id, old_tp_id in cursor.fetchall():
                     if old_tp_id != primary_pid:
                         auditor.log_update("SongAlbums", f"{song.source_id}-{a_id}", {"TrackPublisherID": old_tp_id}, {"TrackPublisherID": primary_pid})
            cursor.execute("UPDATE SongAlbums SET TrackPublisherID = ? WHERE SourceID = ?", (primary_pid, song.source_id))

    def sync_tags(self, song: Song, cursor: sqlite3.Cursor, auditor: Optional[AuditLogger] = None) -> None:
        """Sync unified tags (Category:Name)."""
        if song.tags is None:
            return

        desired_ids = set()
        for t in song.tags:
            if not t or not t.strip(): continue
            
            if ":" in t:
                category, name = t.split(":", 1)
                category = category.strip()
                name = name.strip()
            else:
                from ...core.registries.id3_registry import ID3Registry
                cats = ID3Registry.get_all_category_names()
                category = cats[0] if cats else "Genre"
                name = t.strip()
            
            if not name: continue
            
            cursor.execute("SELECT TagID FROM Tags WHERE TagName = ? COLLATE UTF8_NOCASE AND TagCategory = ?", (name, category))
            row = cursor.fetchone()
            if row:
                desired_ids.add(row[0])
            else:
                cursor.execute("INSERT INTO Tags (TagName, TagCategory) VALUES (?, ?)", (name, category))
                new_id = cursor.lastrowid
                desired_ids.add(new_id)
                if auditor:
                    auditor.log_insert("Tags", new_id, {"TagName": name, "TagCategory": category})

        cursor.execute("SELECT TagID FROM MediaSourceTags WHERE SourceID = ?", (song.source_id,))
        current_ids = set(r[0] for r in cursor.fetchall())

        to_add = desired_ids - current_ids
        to_remove = current_ids - desired_ids

        for tid in to_remove:
            cursor.execute("DELETE FROM MediaSourceTags WHERE SourceID = ? AND TagID = ?", (song.source_id, tid))
            if auditor:
                auditor.log_delete("MediaSourceTags", f"{song.source_id}-{tid}", {"SourceID": song.source_id, "TagID": tid})
        
        for tid in to_add:
            cursor.execute("INSERT INTO MediaSourceTags (SourceID, TagID) VALUES (?, ?)", (song.source_id, tid))
            if auditor:
                auditor.log_insert("MediaSourceTags", f"{song.source_id}-{tid}", {"SourceID": song.source_id, "TagID": tid})
