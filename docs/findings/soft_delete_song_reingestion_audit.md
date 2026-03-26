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

## Status
- [x] Reproduced via test suite in `tests/repro/` (reverted).
- [x] Refined Remediation Plan (Automatic Reconnection via 1-Method Guard).
- [ ] Implementation in `CatalogService` and Repositories.
- [ ] Integration Tests for "Song Wake-Up" protocol.
