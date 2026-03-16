# GOSLING2 Phase 2: Project Metabolism & Library Integration

The current Phase 1.9 established a high-fidelity **Read-Only** view of existing data. Phase 2 focuses on the "Metabolic" functions: ingesting new music, calculating consistent identities, and enabling the first write operations.

## 1. Step 2.1: The Identity Core (Fingerprinting)
We must ensure that GOSLING2 identifies duplicates correctly by hashing only audio frames, ignoring metadata changes.
- [x] **Task**: Implement `src/utils/audio_hash.py` using the Legacy SHA256 logic (skipping ID3v2 header/ID3v1 footers). [DONE]
- [x] **Task**: Implement `src/services/metadata_service.py` to extract high-fidelity tags (ISRC, BPM, Multi-Performers) from physical files. [DONE]

## 2. Step 2.2: Library Lifecycle (Ingestion & Pruning)
Establish the ability to actually *add* music to the database.
- **Task**: `POST /api/v1/catalog/ingest`
    - Logic: Path -> Hash -> Duplicate Check -> Metadata Extract -> ACID Insert.
- **Task**: `DELETE /api/v1/catalog/songs/{song_id}`
    - Logic: Support "Soft Delete" (IsActive=0) vs "Purge" (Remove from DB).

## 3. Step 2.3: Deep Search & Filtering
Search is currently limited to `Songs.MediaName LIKE %q%`.
- **Task**: Expand Search logic to join `Credits` and `Albums`.
    - Searching for "Nirvana" should return all songs where Nirvana is a Performer.
    - Searching for "Nevermind" should return all songs on that album.
- **Task**: Implement UI Filter Pills (Genre, Year Range).

## 4. Step 2.4: The Editor (Write Proof-of-Concept)
Prove that we can modify data safely.
- **Task**: `PATCH /api/v1/songs/{song_id}` - Single song updates.
- **Task**: Finalize `BaseRepository._log_change` integration for auditing.
- **Task**: Implement "Single Song Save" in the Dashboard Detail Panel.

## 5. Metadata Scars & Constraints
- **Hashing**: Use SHA256 (Skips ID3v2/v1). Do NOT hash the whole file.
- **BPM/ISRC**: These are critical fields for Gosling workflows. Ensure the scanner prioritizes these.
- **M2M Publishers**: Maintain the bridge logic established in Phase 1.9.
- **Quality check**: [CONFIRMED] Verified new hash function against 10 existing files in the DB. 100% compatibility achieved.
