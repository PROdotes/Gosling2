# IMPLEMENTATION PLAN: Ingestion V1 Write Path (Complete)

This plan focuses on implementing the missing write orchestration and frontend integration for the Ingestion MVP.

## 1. Phase: Repository Verification
- [x] **Task 1.1**: Verify `SongRepository.insert` and `MediaSourceRepository.delete` work as intended. (VERIFIED)

## 2. Phase: Service Layer Orchestration
- [x] **Task 2.1**: Implement `CatalogService.ingest_file(staged_path)`. (VERIFIED)
- [x] **Task 2.2**: Implement `CatalogService.delete_song(song_id)`. (VERIFIED)

## 3. Phase: API Integration
- [x] **Task 3.1**: Implement `POST /upload` in `src/engine/routers/ingest.py`. (VERIFIED)
- [x] **Task 3.2**: Implement `DELETE /songs/{id}` in `src/engine/routers/ingest.py`. (VERIFIED)

## 4. Phase: Frontend "Drop and Done"
- [x] **Task 4.1**: Update `src/static/js/dashboard/api.js` with `uploadFile(file)` and `deleteSong(id)`. (VERIFIED)
- [x] **Task 4.2**: Connect `IngestDashboard` to `uploadFile`. (VERIFIED)
    - Workflow: Drop -> Instant Upload -> Result Card -> Refresh.
- [x] **Task 4.3**: Add "Delete" button functionality to the Library. (VERIFIED)
