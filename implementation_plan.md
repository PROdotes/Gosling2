# Incomplete Song Filter Implementation Plan

## Goal Description
Implement a feature to filter and manifest "incomplete" songs in the library view. A "complete" song is defined by a set of criteria specified in a JSON file (e.g., must have a title, at least one performer, minimum duration). The user can toggle a "Show Incomplete Only" mode to identify songs that need metadata attention.

## User Review Required
> [!NOTE]
> The criteria for "completeness" are defined in `src/completeness_criteria.json`. Currently, this supports checking fields present in the main library view (Title, Performer, Duration, BPM, Composer) and basic logic (presence, minimum numerical value).

## Proposed Changes

### Configuration
#### [NEW] [completeness_criteria.json](file:///c:/Users/prodo/Antigrav projects/Gosling2/Gosling2/src/completeness_criteria.json)
- JSON file defining the validation rules for ALL tracked fields.
- Structure maps field names to their validation rules (required/optional, constraints).
- Example structure:
    ```json
    {
        "fields": {
            "title": { "required": true, "type": "string" },
            "performers": { "required": true, "type": "list", "min_length": 1 },
            "duration": { "required": true, "type": "number", "min_value": 30 },
            "bpm": { "required": false, "type": "number" },
            "composers": { "required": false, "type": "list" },
            "lyricists": { "required": false, "type": "list" },
            "producers": { "required": false, "type": "list" },
            "groups": { "required": false, "type": "list" },
            "path": { "required": true, "type": "string" },
            "file_id": { "required": true, "type": "number" }
        }
    }
    ```

### Presentation Layer
#### [MODIFY] [library_widget.py](file:///c:/Users/prodo/Antigrav projects/Gosling2/Gosling2/src/presentation/widgets/library_widget.py)
- **UI**: Add `QCheckBox` "Show Incomplete" to the top controls area.
- **Logic**:
    - Load `completeness_criteria.json` on init.
    - Implement `_is_incomplete(row_data, song_object)` method.
        - *Note*: Row data might not have all fields (like lyricists), so we might need to rely on the `LibraryService` to fetch the full song object or check what's available in the model.
        - For efficient filtering in the view without fetching every full song, we might initially filter on what's in the columns (Title, Performer, Duration). If deeper checking is required, we might need a more complex approach or just stick to column data for the live filter.
        - **Decision**: The filter will primarily validate against the `Song` model fields. If the table view only has partial data, we will map the table columns to the JSON keys where possible.

### Tests
#### [NEW] [tests/unit/test_criteria_sync.py](file:///c:/Users/prodo/Antigrav projects/Gosling2/Gosling2/tests/unit/test_criteria_sync.py)
- **Goal**: Ensure `completeness_criteria.json` covers all database fields and roles.
- **Test Strategy**:
    - Initialize a temporary in-memory database using `BaseRepository`.
    - **Introspect Files Table**: 
        - Query `PRAGMA table_info(Files)` to get all column names.
        - Map valid business columns (e.g., `Title`, `Duration`, `TempoBPM`) to expected JSON keys (`title`, `duration`, `bpm`).
    - **Introspect Roles**:
        - Query `SELECT Name FROM Roles` to get all dynamic roles.
        - Map roles to pluralized keys (e.g., `Performer` -> `performers`).
    - **Validation**:
        - Load `src/completeness_criteria.json`.
        - Assert that the JSON config contains entries for ALL discovered columns and roles.
        - Fail if the database has a column/role that isn't defined in the validation rules.
- This ensures that if a new column is added to `Files` or a new Role is inserted, the test forces an update to the criteria.

## Verification Plan

### Manual Verification
1.  **Setup**: Ensure `completeness_criteria.json` exists with strict rules (e.g., min duration 30s).
2.  **Launch App**: Run `python app.py`.
3.  **Import**: Import a mix of complete songs and short/empty-metadata clips.
4.  **Test Toggle**:
    - Click "Show Incomplete".
    - Verify only songs missing metadata or too short are shown.
    - Uncheck "Show Incomplete".
    - Verify all songs are shown.
5.  **Modify Criteria**: Edit the JSON (e.g., remove "performer" requirement) and restart/refresh to verify the filter updates.
