# INGESTION V1 STAGING PLAN

This document outlines the multi-step migration from a Read-Only system to Active Ingestion.

---

## Phase 3.1: Frontend Orchestration (Verified)
- [x] Create dedicated Ingestion Panel in dashboard.
- [x] Implement "Check Path" via `CatalogService.check_ingestion`.
- [x] Fix: Better error reporting for 400 (File Not Found).
- [x] Feature: Absolute path reconstruction for Downloads folder.

## Phase 3.2: Managed Binary Ingestion (Next Step)
- [ ] Implement `POST /api/v1/ingest/upload` (multipart/form-data).
- [ ] Create `StorageService` to handle `temp/library/` staging.
- [ ] Use `rules.json` to calculate target library paths in "Z:\Songs\":
    - Example: `{year}/{artist} - {title}.mp3`
- [ ] Move file from staging to permanent library location.
- [ ] Atomically create `MediaSources` and `Songs` entries.

## Phase 3.3: Pruning & Deletion
- [ ] Implement Deletion API (Pending User Protocol).
- [ ] Integrate with `AuditService` to log the purge event.
- [ ] Ensure orphan records (Credits/Albums) are handled.

## Phase 3.4: Deep Reconciliation (Metadata V1)
- [ ] Resolve `Identities` (Artist Aliases).
- [ ] Resolve `Albums` and `Publishers`.
- [ ] Map all remaining IDs into `SongCredits` and `SongAlbums`.
- [ ] Finalize the "Done" state for fully ingested tracks.
- **Endpoint**: `DELETE /api/v1/catalog/songs/{id}`
- **Logic**: 
  1. Set `IsActive = 0` in `Songs`.
  2. Call `AuditService` to log the deletion action.
---

## Phase 3.4: Deep Reconciliation (Actual Metadata)
**Goal**: Full tag-to-domain mapping.
- **Logic**: 
  1. Use `MetadataService` and `MetadataParser`.
  2. Resolve or Create `Identities`.
  3. Create `SongCredits`.
  4. Link `Albums`.
- **Validation**: Test with files that have NO metadata (Ensuring graceful "Unknown" fallback).
