# GOSLING2 Phase 2: Project Metabolism & Library Integration

The current Phase 1.9 established a high-fidelity **Read-Only** view of existing data. Phase 2 focuses on the "Metabolic" functions: ingesting new music, calculating consistent identities, and enabling the first write operations.

## 1. Step 2.1: The Identity Core (Fingerprinting)
We must ensure that GOSLING2 identifies duplicates correctly by hashing only audio frames, ignoring metadata changes.
- [x] **Task**: Implement `src/utils/audio_hash.py` using the Legacy SHA256 logic (skipping ID3v2 header/ID3v1 footers). [DONE]
- [x] **Task**: Implement `src/services/metadata_service.py` to extract high-fidelity tags (ISRC, BPM, Multi-Performers) from physical files. [DONE]

## 2. Step 2.2: Library Lifecycle (Ingestion & Pruning) [IN PROGRESS]
Establish the ability to actually *add* music to the database.
- [ ] **Task**: `POST /api/v1/catalog/ingest`
    - Logic: Path -> Hash -> Duplicate Check -> Metadata Extract -> ACID Insert.
- [ ] **Task**: `DELETE /api/v1/catalog/songs/{song_id}`
    - Logic: Hard Delete (Remove from DB). Note: IsActive is NOT a soft-delete flag.

## 2.5. Step 2.5: Identity Resolution [DONE]
- [x] **Task**: Implement `IdentityRepository` with bidirectional Tree expansion (Aliases, Members, Groups).
- [x] **Task**: Implement `GET /api/v1/identities/{id}` for full context.
- [x] **Task**: Update Search to use Identity Resolution for deep discovery (Artist Names, Identities, Albums).

## 3. Step 2.3: Deep Search & Filtering [DONE]
Search is currently limited to `Songs.MediaName LIKE %q%`.
- [x] **Task**: Expand Search logic to join `Credits` and `Albums`.
- [x] **Task**: Implement full "Identity Resolution" in search (Searching for "Dave Grohl" returns Nirvana).
- [ ] **Task**: Implement UI Filter Pills (Genre, Year Range).


## 4. Step 2.6: The Artist Browser (Next Chat) [DONE]
Current Status: Backend is 90% ready. Navigation bridges are in place.
- [x] **Task**: Implement **Artist Directory** API for browsing the entire library.
- [x] **Task**: Build the **`/artists/{id}` UI** (The Universal Tree View).
- [x] **Task**: Complete the **Reverse Credit** endpoint to populate the browse catalog.
- [x] **Task**: Audit `schema.py` for remaining "Dark Data" (Publishers, Audit Logs). [DONE]



## 5. Metadata Scars & Constraints
- **Hashing**: Use SHA256 (Skips ID3v2/v1). Do NOT hash the whole file.
- **BPM/ISRC**: These are critical fields for Gosling workflows. Ensure the scanner prioritizes these.
- **M2M Publishers**: Maintain the bridge logic established in Phase 1.9.
- **Quality check**: [CONFIRMED] Verified new hash function against 10 existing files in the DB. 100% compatibility achieved.
