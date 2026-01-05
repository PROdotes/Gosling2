
# Session - Jan 5 2026

## Work Done
1.  **Fixed Duration Import Bug**: Found that `SongRepository.insert` was missing `SourceDuration`, `SourceNotes`, and `AudioHash` in the SQL statement. Added regression test and fixed query.
2.  **Implemented Safe Save Protocol**: Swapped `ExportService` logic to **Write to DB First**, then **Write to ID3**. If DB fails, file is untouched. If ID3 fails, DB is saved but user is warned. Updated `test_export_service.py` to enforce this.
3.  **Refined Audit Logging**: 
    *   **Updates (Smart Diff)**: `_compute_diff` now treats `None` and `""` as equivalent. This prevents useless "Nothing to Nothing" update logs, which is critical for future Undo logic.
    *   **Inserts/Deletes (Verbose)**: Reverted previous filtering filter so "Empty Writes" (e.g. inserting an empty list) ARE logged, ensuring full raw visibility of the data state as requested.
4.  **Verified Functionality**: All critical tests (`test_export_service`, `test_generic_repository`, `test_song_repository`) are passing.

## Next Steps
*   [ ] **T-91 M2M Schema**: Begin work on Album Artist Many-to-Many schema.
*   [ ] **Chip Instant Save**: Improve ChipTray UX.
