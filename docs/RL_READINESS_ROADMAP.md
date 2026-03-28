# GOSLING2: RL Readiness & Real-Life Usability Roadmap

This document serves as the "Master Plan" for transforming GOSLING2 from a metadata database into a production-ready music manager capable of handling Reinforcement Learning (RL) agents and Real-Life (RL) library scale.

## 1. Project Context & Philosophy
GOSLING2 is built on a "Document-First" strategy. We prioritize architectural integrity and data consistency (Soft-Deletes, Transactional Writes) to ensure that the library stays healthy even after millions of automated agent updates.

---

## 2. The Four Pillars of the MVP

### Pillar A: Discovery Engine (Advanced Filters)
- **Status**: Specced, but 0% implemented in UI.
- **Goal**: Enable complex library traversal beyond basic text search.
- **Requirements**: 
    - Sidebar with Logic Toggles (ALL/ANY).
    - Filters: Decade, Genre, Artist, Identity Type (Person/Group/Alias), Publisher.

### Pillar B: Workflow Engine (Lifecycle Management)
- **Status**: Backend implemented (Processing Status), Frontend in progress.
- **Goal**: A clear state-machine for music review.
- **Lifecycle**: 
    - `Status 2 (Imported)`: Raw data, needs verification.
    - `Status 1 (Auto-checked)`: Guessed metadata, ready for human touch.
    - `Status 0 (Reviewed)`: Finalized. Only then can `is_active` (Airplay) be enabled.

### Pillar C: Metabolic Foundation (Relationship CRUD)
- **Status**: Backend 100%, Frontend 30% (Scalars only).
- **Goal**: Allow users to edit Artists, Albums, and Tags directly from the UI.
- **Essential for MVP**: Status 0 cannot be reached without adding Composers and Publishers.

### Pillar D: Core Experience (Audio Player)
- **Status**: Planned.
- **Goal**: Essential for verifying music during the review phase.
- **Requirements**:
    - Global Playback Footer (Persistent).
    - `/api/v1/songs/{id}/stream` endpoint.
    - Basic audio waveform viz (Nice to have for MVP).

---

## 3. High-Level "Archivist" Requirements (Advanced MVP)

### 3.1 Bulk Metadata Editing
- **Need**: Managing thousands of songs is impossible 1-by-1.
- **Feature**: Multi-select in the Dashboard + a "Bulk Actions" drawer to apply shared attributes (Genre, Album, Year).

### 3.2 Advanced Conflict Inbox (Deduplication)
- **Need**: Modern ingestion workflow for mass imports.
- **Feature**: A "Resolve" screen that shows side-by-side metadata comparisons and allows the user to Merge, Skip, or Replace existing records.

### 3.3 Physical Library Sync (Write-back)
- **Need**: Keeping the filesystem consistent with the database.
- **Feature**: Background service to write GOSLING2 metadata to ID3/FLAC tags on the physical file.

---

## 4. Library Hygiene & Maintenance

### 4.1 Unlinked Entity Cleanup
- **Goal**: Removing "Dead" Artists/Albums that have no songs linked to them.
- **Feature**: A "Maintenance" tab in the dashboard for pruning orphaned metadata nodes.

### 4.2 Ghost Record Reactivation
- **Goal**: Handling re-ingestion of previously soft-deleted content.
- **Status**: Implemented (Upsert Wake-up logic).

---

## 5. Summary Tracking since Session Start

1. **Hygiene Discussion**: Acknowledged the need for orphaned entity cleanup as a "Good to have" but secondary to core playback.
2. **Song Workflow Spec**: Finalized the `ProcessingStatus` definitions and mandatory fields for "Approval."
3. **Playback Gaps**: Identified that audio streaming and the player component are the largest missing functional gaps for RL readiness.
4. **Relationship Mutation**: Confirmed that completing the UI for adding Artists/Tags is the current development blocker.
