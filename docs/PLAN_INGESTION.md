# GOSLING3 Spec: Library Ingestion & Pruning (Step 2.2)

## Overview
Phase 2.2 transitions the system from Read-Only to **Active Ingestion**. We will implement the first "Write" operations using the `AudioHash` and `MetadataService` built in previous steps.

---

## 1. Step 2.2.1: The Ingestion Pipeline (`POST /api/v1/catalog/ingest`)
**Goal**: Add a file to the library, ensuring no duplicates and high-fidelity metadata.

### A. Service Layer (`IngestionService`)
- **Inputs**: Absolute file path.
- **Workflow**:
  1. **Calculate Hash**: Use `audio_hash.calculate_hash(path)`.
  2. **Duplicate Check**: Query `SongRepository.get_by_hash(hash)`.
     - If exists: Return existing Song record with `status: ALREADY_EXISTS`.
  3. **Metadata Extract**: Use `MetadataService.extract_metadata(path)`.
  4. **Atomic Insert (Transaction)**:
     - `MediaSources` (Insert & get ID).
     - `Songs` (Insert SourceID).
     - `ArtistNames`/`Identities` (Search-or-Create based on metadata).
     - `SongCredits` (Bridge).
     - `Albums`/`SongAlbums` (Bridge).
     - `Tags` (Bridge).

---

## 2. Step 2.2.2: Pruning (`DELETE /api/v1/catalog/songs/{id}`)
**Goal**: Remove records (Hard Delete).

### A. Repository Layer (`SongRepository`)
- **Purge**: `DELETE FROM MediaSources` (Cascades to all tables).
- **Note**: `IsActive = 0` is NOT a soft-delete flag. It represents airplay eligibility.

---

## 3. UI Integration
- Placeholder for "Ingest" button in the Dashboard (Phase 3 mostly, but API first).

---

## 4. Testing
- Test with duplicate files (same audio, different tags) -> Should NOT create new record.
- Test with new artists/albums -> Should create new Identity/Album records.
