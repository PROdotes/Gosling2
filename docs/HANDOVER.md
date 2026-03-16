# GOSLING2 Phase 2.1 Handoff: Metadata Reading (The "Dumb Reader" Milestone)

## 1. Accomplishments (Core Integrity & Extraction)
We have successfully decoupled **Reading** from **Mapping**.
- **MetadataService (Dumb Reader)**: Refactored `src/services/metadata_service.py` into a pure, stateless conduit.
- **Fidelity First**: It now extracts ALL frames from a file with 100% fidelity. Keys are raw ID3 IDs (e.g., `TPE1`, `TIPL`).
- **Delimiter Safety**: Uses a specific set of safe delimiters (`\u0000`, `|||`, and ` / `) to prevent breaking band names like "Earth, Wind & Fire".
- **Real-World Proved**: Successfully extracted high-fidelity metadata from `Skrillex, ISOxo - Fuze.mp3`, resolving complex `TIPL` involved-people lists into clean string lists.
- **Stateless Read**: The service has NO knowledge of the database schema or JSON mapping. It is 100% localized and future-proof.

## 2. Testing & Quality (Done and Green)
- **Dumb Reader Tests**: `tests/test_metadata_service.py` is updated to verify raw extraction, list fidelity, and delimiter splitting. All 6 tests pass.
- **Coverage**: Logic for complex mutagen objects (like the `TIPL` roles) is now fully tested and verified against real-world tagging "scars".

## 3. Important Lessons (The "Scars")
- **Mapping is a Second Step**: Trying to map fields *during* extraction causes data loss and prevents localization. The Reader must stay dumb.
- **Delimiter Trap**: Common characters like `/` or `;` are dangerous as delimiters. Only the ` / ` (with spaces) and `\u0000` (null) are safe enough for initial reading.
- **Data Doubling**: Frame duplication (e.g., producers in both `TXXX` and `TIPL`) is a reality. The Reader returns both; the Parser must deduplicate.

## 4. Immediate Next Steps (Fresh Session)
1.  **Metadata Parser**: Create a new service (e.g., `MetadataParser`) to take the "Dumb Read" and map it to the database schema using `json/id3_frames.json`.
2.  **Deduplication Logic**: Implement the merge/dedupe logic in the Parser to handle frame doubling.
3.  **Ingestion API**: Orchestrate the Hash -> Read -> Parse -> Insert flow.

## 5. Metadata Map
- **Location**: `json/id3_frames.json` is now the "Map of the Territory" but is NO LONGER loaded by the Service. It is strictly for the upcoming Parser.
- **Structure**: All logic for "Genre" vs "Žanr" lives here and will guide the Parser.
