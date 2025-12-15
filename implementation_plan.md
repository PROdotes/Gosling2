# Added RecordingYear Field Implementation Plan

## Goal Description
Add a `RecordingYear` field to the Song entity and Database. This allows users to track the year of recording for their music library.

## User Review Required
> [!IMPORTANT]
> This requires a database schema change. Existing databases will need to be migrated or recreated. Since we haven't implemented a formal migration system yet, we might rely on `CREATE TABLE IF NOT EXISTS` not adding columns to existing tables. **The valid approach for dev is to recreate the DB or manually execute the ALTER TABLE.**
> For this task, I will support the `BaseRepository` to attempt an `ALTER TABLE` if the column is missing, or rely on the user to reset the DB logic if that's the established pattern.
> *Decision*: I will modify `_ensure_schema` to check for the column and add it if missing, ensuring a smooth transition.

## Proposed Changes

### Data Layer
#### [MODIFY] [src/data/models/song.py](file:///c:/Users/prodo/Antigrav projects/Gosling2/Gosling2/src/data/models/song.py)
 - Add `recording_year: Optional[int] = None`

#### [MODIFY] [src/data/repositories/base_repository.py](file:///c:/Users/prodo/Antigrav projects/Gosling2/Gosling2/src/data/repositories/base_repository.py)
 - Update `CREATE TABLE Files` definition.
 - Add logic to `_ensure_schema` to `ALTER TABLE Files ADD COLUMN RecordingYear INTEGER` if it doesn't exist (Migration logic).

#### [MODIFY] [src/data/repositories/song_repository.py](file:///c:/Users/prodo/Antigrav projects/Gosling2/Gosling2/src/data/repositories/song_repository.py)
 - Update `add_song` (INSERT query).
 - Update `update_song` (UPDATE query).
 - Update `_song_from_row` (Mapping).

### Tests
#### [MODIFY] [tests/unit/data/test_schema_model_cross_ref.py](file:///c:/Users/prodo/Antigrav projects/Gosling2/Gosling2/tests/unit/data/test_schema_model_cross_ref.py)
 - Update `db_to_model_map` and `model_to_db_map` to include `RecordingYear`.

### Presentation Layer
#### [MODIFY] [src/presentation/widgets/library_widget.py](file:///c:/Users/prodo/Antigrav projects/Gosling2/Gosling2/src/presentation/widgets/library_widget.py)
 - Add `COL_YEAR` constant.
 - Update `COL_TO_FIELD` map.
 - Ensure the new column is displayed in `_populate_table`.

## Verification Plan
1. **Safety Check Failure**: Run `test_schema_model_cross_ref.py` after modifying Model but before Test Mapping to see it catch the discrepancy.
2. **End-to-End Test**:
    - Run the App.
    - Drag & Drop a file.
    - Verify Year is saved (if extracted? Note: I might need to update MetadataService to extract Year).
3. **Automated Tests**:
    - Run `test_schema_model_cross_ref.py` (Pass after all changes).
    - Run `test_library_widget_filtering.py` (Ensure no regressions).
