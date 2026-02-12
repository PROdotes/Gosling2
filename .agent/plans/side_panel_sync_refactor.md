# SidePanel Baseline Synchronization Plan

The SidePanelWidget maintains a "Staging Buffer" for text fields (Title, Year, etc.) while directly committing "Instant Changes" (Artists, Albums, Tags) to the database. Currently, the SidePanel's internal song objects (the "Baseline") become stale after an instant change, causing validation and the "Finalize Prompt" to fail or lag.

## 1. Unified Synchronization Method
Implement `_sync_baseline_from_db()` in `SidePanelWidget`:
*   Loop through `self.current_songs` and refetch each from the database.
*   Update `self.current_songs` with fresh objects.
*   Propagate the new song list to all `EntityListWidget` adapters to ensure consistency.
*   Call `_refresh_field_values()` to update the UI labels (e.g. recalculated Performers string).

## 2. Integration Points
*   **Pre-Save Sync**: Call `_sync_baseline_from_db()` at the very beginning of `_on_save_clicked()`.
    *   This ensures the "Ready to Finalize" check looks at the actual DB state + current staged text.
*   **Real-time Adapter Refresh**: Update `_on_entity_data_changed` and the `SongFieldAdapter` callbacks to use this centralized sync.
    *   When a chip is added/removed (Instant DB write), the SidePanel baseline updates immediately.

## 3. Validation Logic
*   Keep the `_get_song_validation_errors(song, projected_changes)` pattern.
*   Because the `song` object is now always fresh (post-sync), the validator will correctly see that a required Artist or Album was added.

## 4. Key Improvements
*   **Eliminate Redundancy**: Removes scattered manual refetching logic in favor of one authoritative sync method.
*   **Fixes "Two-Clock" Bug**: The "Ready to Finalize?" prompt will now trigger on the *first* save click because the baseline is refreshed before the check occurs.
*   **Preserves UI State**: Does not rebuild the entire property grid, maintaining scroll position and focus.
