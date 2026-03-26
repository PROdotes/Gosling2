# Audit: Soft-Delete Song Re-Ingestion Behavior

## Overview
This document outlines the behavior of the **GOSLING2** ingestion engine when encountering files that match previously **soft-deleted** (`IsDeleted=1`) records in the database.

During a technical audit of the `CatalogService` and `SongRepository`, two critical edge cases were identified where the system either fails to handle existing soft-deleted data or incorrectly duplicates it.

---

## Technical Findings

### 1. Path Collision (The "Unique Crash")
When a song file is re-ingested at the **exact same filesystem path** as a soft-deleted record:
- **Result**: **System Crash** (`sqlite3.IntegrityError: UNIQUE constraint failed: MediaSources.SourcePath`).
- **Root Cause**: 
    1. `CatalogService.check_ingestion` performs a lookup via `get_by_path`.
    2. `MediaSourceRepository.get_by_path` strictly filters for `IsDeleted = 0`.
    3. The service receives `None`, assumes the song is **NEW**, and triggers a hard `INSERT`.
    4. The database-level `UNIQUE` constraint on `MediaSources.SourcePath` triggers, causing the transaction to fail.

### 2. Hash Match (The "Stealth Duplicate")
When a song file with the **same audio hash** is ingested at a **different path** (e.g., moved to a different folder) after being soft-deleted:
- **Result**: **Duplicate Record Created**.
- **Root Cause**: 
    1. `get_by_hash` also filters for `IsDeleted = 0`.
    2. The service ignores the existing (deleted) "ghost" record and creates a second active record for the same audio content.
    3. The database now contains two distinct `SourceID`s for the same hash—one active and one deleted—leading to inconsistent history and "Split-Brain" states.

---

## Architectural Discrepancy: Metadata vs. Songs

The project currently implements a **Hybrid Soft-Delete Protocol** where "Reference Data" handles re-ingestion much more gracefully than "Target Data" (Songs).

| Entity Category | Entity Type | Re-Ingestion Behavior (if Soft-Deleted) |
| :--- | :--- | :--- |
| **Reference Data** | **Tags, Albums, Artists, Publishers** | **Wake-Up (Reconnect)**: Flips `IsDeleted=0` and reuses the existing ID. |
| **Target Data** | **Songs (MediaSources)** | **Crash or Duplicate**: No reconnection logic exists in the repository. |

---

## Proposed Remediation (Discussion Required)

To align Songs with the rest of the ecosystem and prevent ingestion crashes, the following changes are proposed:

1.  **Toggle-Aware Lookup Guard**:
    - Implement a `status_check(path, hash)` method in `MediaSourceRepository` that ignores the `IsDeleted` filter.
    - Update `CatalogService.check_ingestion` to call this guard *before* assuming a song is `NEW`.
    - If found with `IsDeleted=1`, return a specific `status: "SOFT_DELETED_MATCH"` report.

2.  **Implementation of "Automatic Song Reconnection"**:
    - When `SOFT_DELETED_MATCH` is detected, `CatalogService.ingest_file` will perform an `UPDATE MediaSources SET IsDeleted = 0 WHERE SourceID = old_id`.
    - It then proceeds to call the existing relationship insert methods (`insert_credits`, `insert_tags`, `insert_albums`) using that `old_id`.
    - **Note**: Since junction links were purged on soft-delete, this "Wake-Up" process is functionally identical to a fresh insert but preserves the original database ID.

3.  **The "Unique Index" Precedence**:
    - Acknowledge that the dynamic index in `BaseRepository` (`idx_mediasources_audiohash`) makes this fix mandatory to avoid crashes on duplicate audio hashes.

---

## Implementation Plan (Code Reference)

### Files to Change

| File | Change |
| :--- | :--- |
| `src/data/media_source_repository.py` | Add `find_deleted_by_path()` and `find_deleted_by_hash()` methods; add `wake_up()` method |
| `src/data/song_repository.py` | Add `reinsert_song()` method that reuses an existing SourceID |
| `src/services/catalog_service.py` | Add soft-delete guard to `check_ingestion()`; add reconnection branch to `ingest_file()` |

---

### Step 1: MediaSourceRepository — Soft-Delete-Aware Lookups + Wake-Up

**Location:** `src/data/media_source_repository.py`

Two new query methods that look for soft-deleted ghosts, plus a wake-up writer. These sit alongside the existing `get_by_path` / `get_by_hash` (which keep their `IsDeleted = 0` filter for normal reads).

```python
# --- New methods in MediaSourceRepository ---

def find_deleted_by_path(self, path: str) -> Optional[MediaSource]:
    """
    Look for a soft-deleted MediaSource at this exact path.
    Used by the ingestion guard ONLY — normal reads should still use get_by_path().
    """
    logger.debug(f"[MediaSourceRepository] -> find_deleted_by_path(path='{path}')")
    with self._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT SourceID, TypeID, MediaName, SourcePath, SourceDuration,
                   AudioHash, IsActive, ProcessingStatus
            FROM MediaSources
            WHERE SourcePath = ? AND IsDeleted = 1
            """,
            (path,),
        )
        row = cursor.fetchone()
        if row:
            source = self._row_to_source(row)
            logger.info(
                f"[MediaSourceRepository] <- find_deleted_by_path() GHOST id={source.id}"
            )
            return source
        return None


def find_deleted_by_hash(self, audio_hash: str) -> Optional[MediaSource]:
    """
    Look for a soft-deleted MediaSource with this audio hash.
    Used by the ingestion guard ONLY.
    """
    logger.debug(f"[MediaSourceRepository] -> find_deleted_by_hash(hash='{audio_hash}')")
    with self._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT SourceID, TypeID, MediaName, SourcePath, SourceDuration,
                   AudioHash, IsActive, ProcessingStatus
            FROM MediaSources
            WHERE AudioHash = ? AND IsDeleted = 1
            """,
            (audio_hash,),
        )
        row = cursor.fetchone()
        if row:
            source = self._row_to_source(row)
            logger.info(
                f"[MediaSourceRepository] <- find_deleted_by_hash() GHOST id={source.id}"
            )
            return source
        return None


def wake_up(self, source_id: int, conn: sqlite3.Connection,
            new_path: Optional[str] = None) -> bool:
    """
    Flip IsDeleted = 0 for a previously soft-deleted MediaSource.
    Optionally update SourcePath if the file moved to a new location.
    Returns True if a row was updated.
    """
    logger.debug(f"[MediaSourceRepository] -> wake_up(id={source_id}, new_path={new_path})")
    cursor = conn.cursor()

    if new_path:
        cursor.execute(
            "UPDATE MediaSources SET IsDeleted = 0, SourcePath = ? WHERE SourceID = ? AND IsDeleted = 1",
            (new_path, source_id),
        )
    else:
        cursor.execute(
            "UPDATE MediaSources SET IsDeleted = 0 WHERE SourceID = ? AND IsDeleted = 1",
            (source_id,),
        )

    updated = cursor.rowcount > 0
    if updated:
        logger.info(f"[MediaSourceRepository] <- wake_up(id={source_id}) RESTORED")
    else:
        logger.warning(f"[MediaSourceRepository] <- wake_up(id={source_id}) NO_CHANGE")
    return updated
```

**Design Notes:**
- `find_deleted_by_path` and `find_deleted_by_hash` are **read-only** methods with their own connections (consistent with `get_by_path` / `get_by_hash`).
- `wake_up` takes an **external connection** (like `soft_delete` does) so it participates in the caller's transaction.
- `new_path` parameter handles Bug 2 (hash match at a different path). If `None`, the path stays the same (Bug 1 — same path re-ingestion).

---

### Step 2: SongRepository — Re-Insert Using Existing SourceID

**Location:** `src/data/song_repository.py`

A new method that mirrors the existing `insert()` flow but **skips the MediaSources/Songs INSERT** and just re-links relationships.

```python
# --- New method in SongRepository ---

def reinsert_song(self, source_id: int, song: Song, conn: sqlite3.Connection) -> int:
    """
    Re-link a woken-up MediaSource to its relationships.

    The MediaSource row already exists (just had IsDeleted flipped to 0).
    The Songs extension row already exists (never deleted).
    We only need to re-insert junction rows that were hard-deleted during soft_delete.

    This mirrors insert() steps 3 onward, using the OLD source_id.
    """
    logger.debug(
        f"[SongRepository] -> reinsert_song(id={source_id}, name='{song.title}')"
    )

    tag_repo = TagRepository(self.db_path)
    album_repo = SongAlbumRepository(self.db_path)
    pub_repo = PublisherRepository(self.db_path)
    credit_repo = SongCreditRepository(self.db_path)

    credit_repo.insert_credits(source_id, song.credits, conn)
    tag_repo.insert_tags(source_id, song.tags, conn)
    album_repo.insert_albums(source_id, song.albums, conn)
    pub_repo.insert_song_publishers(source_id, song.publishers, conn)

    logger.info(
        f"[SongRepository] <- reinsert_song() RELINKED ID={source_id} '{song.title}'"
    )
    return source_id
```

**Design Notes:**
- The `Songs` extension row (TempoBPM, RecordingYear, ISRC) was **never deleted** during soft-delete — only `MediaSources.IsDeleted` was flipped and junction rows were purged. So we don't re-insert into `Songs`.
- **Open question:** Should we UPDATE the Songs extension row with new metadata? (e.g., if BPM/ISRC changed between delete and re-ingest). Likely yes, but could be a follow-up.
- All four relationship repos already have wake-up logic for their own entities (Tags, Albums, ArtistNames), so calling them here correctly handles the case where a tag was also soft-deleted between the song's deletion and re-ingestion.

---

### Step 3: CatalogService — The Ingestion Guard

**Location:** `src/services/catalog_service.py`

Two changes: (A) `check_ingestion` gains a soft-delete guard, and (B) `ingest_file` gains a reconnection branch.

#### A. check_ingestion — Add ghost detection between each collision check

The guard slots in **after** each existing check returns `None`. If the normal `get_by_path` finds nothing, we check `find_deleted_by_path` before moving on.

```python
def check_ingestion(self, file_path: str) -> Dict[str, Any]:
    # ... existing file-exists validation ...

    # 1. Path Check (Fastest)
    existing_by_path = self._song_repo.get_by_path(file_path)
    if existing_by_path:
        # ... existing ALREADY_EXISTS return (unchanged) ...

    # === NEW: Soft-delete path guard ===
    ghost_by_path = self._song_repo.find_deleted_by_path(file_path)
    if ghost_by_path:
        logger.info(
            f"[CatalogService] <- check_ingestion() SOFT_DELETED_PATH_MATCH id={ghost_by_path.id}"
        )
        # Still need metadata for relationship re-linking
        try:
            audio_hash = calculate_audio_hash(file_path)
            raw_meta = self._metadata_service.extract_metadata(file_path)
            parsed_song = self._metadata_parser.parse(raw_meta, file_path)
            parsed_song = parsed_song.model_copy(update={"audio_hash": audio_hash})
        except Exception as e:
            return {"status": "ERROR", "message": f"Metadata failed on ghost match: {str(e)}"}

        return {
            "status": "SOFT_DELETED_MATCH",
            "match_type": "PATH",
            "ghost_id": ghost_by_path.id,
            "song": parsed_song,
        }

    # 2. Hash Check (Requires reading file)
    try:
        audio_hash = calculate_audio_hash(file_path)
    except Exception as e:
        return {"status": "ERROR", "message": f"Hash failed: {str(e)}"}

    existing_by_hash = self._song_repo.get_by_hash(audio_hash)
    if existing_by_hash:
        # ... existing ALREADY_EXISTS return (unchanged) ...

    # === NEW: Soft-delete hash guard ===
    ghost_by_hash = self._song_repo.find_deleted_by_hash(audio_hash)
    if ghost_by_hash:
        logger.info(
            f"[CatalogService] <- check_ingestion() SOFT_DELETED_HASH_MATCH id={ghost_by_hash.id}"
        )
        try:
            raw_meta = self._metadata_service.extract_metadata(file_path)
            parsed_song = self._metadata_parser.parse(raw_meta, file_path)
            parsed_song = parsed_song.model_copy(update={"audio_hash": audio_hash})
        except Exception as e:
            return {"status": "ERROR", "message": f"Metadata failed on ghost match: {str(e)}"}

        return {
            "status": "SOFT_DELETED_MATCH",
            "match_type": "HASH",
            "ghost_id": ghost_by_hash.id,
            "new_path": file_path,  # Path changed — need to update SourcePath
            "song": parsed_song,
        }

    # 3. Metadata check (unchanged) ...
    # 4. Return NEW (unchanged) ...
```

#### B. ingest_file — Add reconnection branch

Currently `ingest_file` only proceeds if `check["status"] == "NEW"`. We add a second accepted status.

```python
def ingest_file(self, staged_path: str) -> Dict[str, Any]:
    # 1. Validation check
    check = self.check_ingestion(staged_path)

    if check["status"] == "SOFT_DELETED_MATCH":
        # === NEW: Song Wake-Up / Reconnection ===
        return self._reconnect_song(check)

    if check["status"] != "NEW":
        # ... existing rejection logic (unchanged) ...

    # ... existing NEW insert logic (unchanged) ...


def _reconnect_song(self, check: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wake up a soft-deleted song and re-link its relationships.
    Mirrors the insert path but reuses the original SourceID.
    """
    ghost_id = check["ghost_id"]
    song = check["song"]
    new_path = check.get("new_path")  # Only set for HASH matches (file moved)

    logger.debug(f"[CatalogService] -> _reconnect_song(ghost_id={ghost_id})")

    conn = self._song_repo.get_connection()
    try:
        # 1. Flip IsDeleted = 0 (and update path if file moved)
        restored = self._song_repo.wake_up(ghost_id, conn, new_path=new_path)
        if not restored:
            conn.rollback()
            return {"status": "ERROR", "message": f"Failed to wake up ghost id={ghost_id}"}

        # 2. Re-link relationships (credits, tags, albums, publishers)
        self._song_repo.reinsert_song(ghost_id, song, conn)

        conn.commit()
        logger.info(f"[CatalogService] <- _reconnect_song() RESTORED ID={ghost_id}")

        hydrated_song = song.model_copy(update={"id": ghost_id})
        return {"status": "RECONNECTED", "song": hydrated_song}

    except Exception as e:
        conn.rollback()
        logger.error(f"[CatalogService] <- _reconnect_song() FAILED: {e}")
        return {"status": "ERROR", "message": f"Reconnection failed: {str(e)}"}
    finally:
        conn.close()
```

---

### Step 4: Integration Test Outline

**Location:** `tests/test_song_reingestion.py` (new file)

```python
class TestSongReingestion:
    """Integration tests for the Song Wake-Up protocol."""

    def test_reingest_same_path_restores_original_id(self, populated_db):
        """Bug 1 fix: re-ingesting at the same path should wake up, not crash."""
        service = CatalogService(populated_db)
        # 1. Get an existing song
        # 2. Soft-delete it
        # 3. Re-ingest the same file path
        # 4. Assert: status == "RECONNECTED"
        # 5. Assert: returned song.id == original_id
        # 6. Assert: song is visible via get_song() again

    def test_reingest_different_path_same_hash_restores_and_updates_path(self, populated_db):
        """Bug 2 fix: same hash at new path should wake up, not duplicate."""
        # 1. Get an existing song, note its hash
        # 2. Soft-delete it
        # 3. Re-ingest with the same hash but a different SourcePath
        # 4. Assert: status == "RECONNECTED"
        # 5. Assert: returned song.id == original_id
        # 6. Assert: SourcePath in DB is now the NEW path
        # 7. Assert: only ONE active record for this hash

    def test_reingest_restores_junction_links(self, populated_db):
        """Wake-up should re-create credits, tags, albums, publishers."""
        # 1. Ingest song with known credits/tags/albums
        # 2. Soft-delete (purges junctions)
        # 3. Re-ingest
        # 4. Assert: all junction links exist again
        # 5. Assert: reference entities (tags, albums) are IsDeleted=0

    def test_reingest_active_song_same_path_returns_already_exists(self, populated_db):
        """Normal collision guard still works — no false wake-ups."""
        # 1. Ingest a song (active, not deleted)
        # 2. Try to ingest again at the same path
        # 3. Assert: status == "ALREADY_EXISTS", match_type == "PATH"

    def test_check_ingestion_reports_soft_deleted_match(self, populated_db):
        """Dry-run check should report SOFT_DELETED_MATCH, not NEW."""
        # 1. Ingest + soft-delete
        # 2. Call check_ingestion() (dry-run)
        # 3. Assert: status == "SOFT_DELETED_MATCH"
        # 4. Assert: ghost_id == original_id
```

---

### Decision Points (For Discussion)

| # | Question | Options | Recommendation |
| :--- | :--- | :--- | :--- |
| 1 | **Should `reinsert_song` update the Songs extension row?** (BPM, ISRC, Year may have changed) | A) No — preserve original metadata. B) Yes — overwrite with new file's metadata. | **B** — the new file is the source of truth. Add `UPDATE Songs SET TempoBPM=?, RecordingYear=?, ISRC=? WHERE SourceID=?` to `reinsert_song`. |
| 2 | **Should `find_by_metadata` also detect ghosts?** (3rd collision check in `check_ingestion`) | A) No — metadata check is already the weakest signal. B) Yes — for completeness. | **A for now** — path and hash cover the crash/duplicate bugs. Metadata ghost detection can be a follow-up if needed. |
| 3 | **What status should the API return?** | A) `"RECONNECTED"` (new status). B) `"INGESTED"` (treat as normal). | **A** — callers should know the ID was reused, not freshly created. The frontend can display "Restored" instead of "Added". |
| 4 | **Should we log/audit the reconnection?** | A) Logger only. B) Add a `ReingestionLog` table. | **A for now** — logger captures it. Audit table is overkill until we have a reporting need. |

---

## Status
- [x] Reproduced via test suite in `tests/repro/` (reverted).
- [x] Refined Remediation Plan (Automatic Reconnection via 1-Method Guard).
- [x] Expanded Implementation Plan with code references.
- [ ] Implementation in `CatalogService` and Repositories.
- [ ] Integration Tests for "Song Wake-Up" protocol.
