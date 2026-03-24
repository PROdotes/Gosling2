# INGESTION V1 - MVP Implementation Spec

## Context
The verification pipeline (`POST /api/v1/catalog/ingest/check`) is complete — path, hash, and metadata collision detection all work. What's missing is the **write path**: uploading a file to staging, inserting it into the DB, and deleting songs. This spec defines the minimal end-to-end ingestion loop for testing.

## Scope
**In:** File upload to staging, auto-ingest (MediaSources + Songs rows only), hard delete, frontend wiring.
**Out:** Credits, albums, tags, publishers insertion. Multi-file/folder support. File routing. Auditing for writes (Deferred).

### Future: File Routing
After ingestion, files will be moved from staging to `LIBRARY_ROOT` (`Z:\Songs`) using genre-based routing rules defined in `docs/configs/rules.json`. For MVP, `source_path` in the DB points to the staging location. Routing is a separate task.

---

## 1. Database Integrity

**File:** `src/data/base_repository.py`

`_get_connection()` must execute both of the following on every new connection:
1. `PRAGMA foreign_keys = ON` — so `ON DELETE CASCADE` between MediaSources and Songs actually fires.
2. `CREATE UNIQUE INDEX IF NOT EXISTS idx_mediasources_audiohash ON MediaSources(AudioHash)` — prevents duplicate files under concurrent writes. `IF NOT EXISTS` makes this a no-op after the first run.

Both live in `_get_connection()` for now. A proper migration system will be introduced when more schema changes land (next phase).

### Pre-flight: Verify Existing Data
Before applying the UNIQUE index, verify no duplicate `AudioHash` values exist in the current DB. If duplicates are found, deduplicate first — the index creation will fail otherwise.

### Connection Pattern
Both `insert()` and `delete()` receive a **connection** from the service layer (see Section 3). Both writes share the same connection — the service layer commits or rolls back as a single atomic unit.

### `insert(song: Song, conn) -> int`
Single transaction inserting into two tables:
1. **MediaSources** — TypeID via `(SELECT TypeID FROM Types WHERE TypeName = 'Song')`, MediaName, SourcePath, SourceDuration (seconds), AudioHash, ProcessingStatus=1, IsActive=1.
2. **Songs** — SourceID (from step 1), TempoBPM, RecordingYear, ISRC.

Returns the new SourceID. Does NOT commit — the service layer owns the commit.

### `delete(song_id: int, conn) -> bool`
1. `DELETE FROM MediaSources WHERE SourceID = ?` — cascade handles the Songs row.

Returns True if a row was deleted. Does NOT commit — the service layer owns the commit.

---

## 3. Service Layer

**File:** `src/services/catalog_service.py`

The service layer owns the DB connection for all write operations. Pattern:
1. Create connection via `_song_repo._get_connection()`.
2. Pass to repo methods.
3. On success: `conn.commit()`.
4. On failure: `conn.rollback()` + clean up staged file (if applicable).

### `ingest_file(staged_path: str) -> Dict[str, Any]`
1. Delegates to the existing `check_ingestion()` against the staged file. The `Song` object built during this step (with metadata, hash, etc.) flows through the pipeline — no double extraction.
2. If `ALREADY_EXISTS` — returns the check result as-is.
3. If `NEW` — creates connection, calls `_song_repo.insert(song, conn)`. On success, attaches the returned `SourceID` onto the Song object (`song.model_copy(update={"id": new_source_id})`), commits, returns `{"status": "INGESTED", "song": <Song with ID>}`.
4. If `ERROR` — returns as-is.
5. **On DB failure:** rollback the transaction AND delete the staged file to prevent orphans. Staged files that fail to ingest should not accumulate in staging.

**Note:** MVP only writes MediaSources + Songs rows. The full Song object (credits, tags, albums) is already parsed and available — additional CRUD will be wired in as tables are added in the next phase.

### `delete_song(song_id: int) -> bool`
1. Fetches the song via `_song_repo.get_by_id()` (need `source_path` for cleanup).
2. Creates connection, calls `_song_repo.delete(song_id, conn)`, commits.
3. **File cleanup for MVP:** If `source_path` is inside `STAGING_DIR`, deletes the physical file. **CRITICAL:** Cleanup must happen only *after* a successful `conn.commit()`. Silently ignores if file is already gone. Non-staged files are DB-only delete — a user-facing "delete from disk?" choice will be added post-MVP.

---

## 4. Endpoints

**File:** `src/engine/routers/ingest.py` (extending existing router at `/api/v1/ingest`)

### `POST /api/v1/ingest/upload`
- Accepts `UploadFile` via multipart/form-data.
- **Extension validation:** Rejects files whose extension is not in `ACCEPTED_EXTENSIONS` (from `config.py`). MVP: `[".mp3"]` only. This list is the single source of truth — update it when adding wav/zip support later.
- Ensures `STAGING_DIR` (`temp/library/staging` from `src/engine/config.py`) exists.
- **UUID filename:** Writes uploaded bytes to `STAGING_DIR / {uuid4}_{original_filename}` to prevent collisions when multiple files share the same name. The original filename is preserved in metadata (MediaName).
- Calls `CatalogService.ingest_file(staged_path)`.
- Returns `IngestionReportView` with status `INGESTED`, `ALREADY_EXISTS`, or `ERROR`.

### `DELETE /api/v1/ingest/songs/{song_id}`
- Calls `CatalogService.delete_song(song_id)`.
- 200 on success, 404 if song not found.

---

## 5. Frontend: API Client

**File:** `src/static/js/dashboard/api.js`

### `uploadAndIngest(file)`
POST multipart to `/api/v1/ingest/upload`. Must NOT set Content-Type header — browser sets multipart boundary automatically.

### `deleteSong(songId)`
DELETE to `/api/v1/ingest/songs/{songId}`.

---

## 6. Frontend: Ingestion Panel

**File:** `src/static/js/dashboard/renderers/ingestion.js`

Drop zone upgrade — `drop` event grabs the `File` object from `e.dataTransfer.files[0]` and calls `uploadAndIngest(file)` directly.

- "Uploading..." state while in flight.
- `INGESTED` → green card with song metadata.
- `ALREADY_EXISTS` → yellow card with match info. Card includes a clickable link to the existing song (navigates to Songs tab and opens the song detail) so the user can quickly inspect the duplicate.
- `ERROR` → red card.
- Path input + Check button remain for path-based verification (existing flow — returns `NEW` or `ALREADY_EXISTS`).

---

## 7. Frontend: Delete in Song Detail

**File:** `src/static/js/dashboard/renderers/songs.js`

Delete button added to `renderSongDetailComplete()` at the bottom of the detail panel. Styled as a danger action. Uses `data-action="delete-song"` with `data-song-id`.

**File:** `src/static/js/dashboard/main.js`

Global click handler picks up `data-action="delete-song"`:
- Confirm dialog: "Delete {title}? This cannot be undone."
- On confirm: `deleteSong(id)` → hide detail panel → refresh song list via `performSearch()`.
- **Error handling:** 404 (already deleted) is treated as success — hide panel, refresh list. 500 or network error shows a toast notification so the user knows the delete failed.

---

## Files Modified

| File | Change |
|---|---|
| `src/data/base_repository.py` | `PRAGMA foreign_keys = ON`, `CREATE UNIQUE INDEX` for AudioHash |
| `src/data/song_repository.py` | `insert()`, `delete()` with audit logging |
| `src/services/catalog_service.py` | `ingest_file()`, `delete_song()` — owns connection + batch_id |
| `src/engine/routers/ingest.py` | `POST /upload` (UUID filename, extension check), `DELETE /songs/{id}` |
| `src/engine/config.py` | `ACCEPTED_EXTENSIONS = [".mp3"]` |
| `src/static/js/dashboard/api.js` | `uploadAndIngest()`, `deleteSong()` |
| `src/static/js/dashboard/renderers/ingestion.js` | Real file upload via drop zone |
| `src/static/js/dashboard/renderers/songs.js` | Delete button in song detail |
| `src/static/js/dashboard/main.js` | Delete action handler with error toast |

---

## Verification

1. Start engine server.
2. **Ingest tab:** drag MP3 onto drop zone → "Ingested" with metadata.
3. Drag same file again → "Already Exists (HASH)" or "(PATH)".
4. **Songs tab:** search for ingested song → appears in results.
5. Open song detail → click Delete → confirm → song removed from list.
6. Drag same file again → ingests as new (hard delete cleared it).
