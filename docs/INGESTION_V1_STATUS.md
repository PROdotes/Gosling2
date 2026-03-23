# Ingestion MVP Handoff (Status: `Data Layer Green`)

This document serves as the handoff bridge between AI sessions for the Ingestion V1 project. 
All data layer infrastructure and modular repository patterns are completed and verified via `pytest`.

## 1. Accomplishments & Structural Patterns
- [x] **Universal MediaSource Repository**: `MediaSourceRepository` owns the base `MediaSources` table and provides a universal `delete(source_id)` with hard-cascades to all specialized tables (e.g., `Songs`).
- [x] **Modular Inheritance**: `SongRepository` inherits from `MediaSourceRepository`, delegating core record creation via `super().insert_source()`.
- [x] **Duration Strategy**: Internal domain models use `duration_ms: int`. The database uses seconds (`REAL`). `MediaSource` model provides a clean `duration_s` property for seamless database transition.
- [x] **Infrastructure**: `BaseRepository` updated to enable `PRAGMA foreign_keys = ON` and a unique `AudioHash` index.

## 2. Open Tasks (The "Next Session" Checklist)

### Metadata & Parsing
- [x] **Fix Extraction Bug**: `MetadataService.extract_metadata` currently ignores duration. Update it to return `(tags: Dict, duration: float)` using `mutagen.File().info.length`.
- [x] **Update Parser**: `MetadataParser.parse` must set `song.duration_s = duration` on the final model.

### Repository Refinement
- [x/] **Universal Reads**: Move `get_by_path` and `get_by_hash` from `SongRepository` to `MediaSourceRepository`. These are universal file attributes and should return the base `MediaSource` model (or the specialized model if overridden).

### Service Layer (Atomic Orchestration)
- [ ] **Implement `CatalogService.ingest_file(staged_path)`**:
    - Workflow: `check_ingestion` → `repo.insert` → `conn.commit()`.
    - Handles transaction lifecycle (commit/rollback) and cleanup on failure.
- [ ] **Implement `CatalogService.delete_song(song_id)`**:
    - Workflow: `repo.delete` → `conn.commit()` → `os.remove(staged_path)`.
    - Ensures physical file deletion occurs ONLY after DB commit.

### API Layer
- [ ] **Update `src/engine/routers/ingest.py`**:
    - `POST /upload`: Handle `FastAPI.UploadFile`, save to `STAGING_DIR`, and call `service.ingest_file`.
    - `DELETE /songs/{song_id}`: Call `service.delete_song`.

### Frontend
- [ ] **Api.js**: Implement `uploadAndIngest()` and `deleteSong()`.
- [ ] **Dashboard JS**: Connect the UI drop zone and the Delete button to these APIs.

## 3. Reference Files
- **Models**: `src/models/domain.py` (`MediaSource`)
- **Repos**: `src/data/media_source_repository.py`, `src/data/song_repository.py`
- **Tests**: `tests/data/test_media_source_repository.py`, `tests/data/test_song_repository_write.py`, `tests/data/test_song_repository_delete.py`
