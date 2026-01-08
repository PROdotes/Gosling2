# Tag Unification Architecture (T-89)

## Overview
As of Jan 2026, the application has moved away from top-level `Genre` and `Mood` fields. All such metadata is now stored in the unified `Tags` system.

## Storage
- **Table**: `MediaSourceTags` (Junction) and `Tags` (Entity).
- **Format**: Tags are categorized. In memory, they are represented as `Category:Name`.
- **Primary Categories**:
  - `Genre`: Formerly the `Genre` field.
  - `Mood`: Formerly the `Mood` field.
  - `Status`: Internal workflow states (e.g., `Status:Unprocessed`).
  - `Custom`: User-defined tags.

## Data Model (`Song`)
The `Song` model contains a single `tags: List[str]` attribute. 
Direct attributes for `genre` and `mood` have been removed.

## ID3 Mapping (Metadata Service)
To maintain compatibility with external players, the `MetadataService` performs dynamic mapping during write:
- `tags` starting with `Genre:` -> Joined by `;` and written to `TCON`.
- `tags` starting with `Mood:` -> Joined by `;` and written to `TMOO`.
- All other tags -> Written as `TXXX:Tag:Name` or handled by user preference.

## UI Representation
- **Side Panel**: A unified `ChipTrayWidget` displays all tags.
- **Library Table**: A virtual "Tags" column can be enabled to show a summarized list.
- **Filters**: The filter tree can still break out "Genre" and "Mood" as separate branches by filtering the tag registry by category.

## Migration
Legacy database columns in `Songs` for `Genre` and `Mood` are deprecated and should not be used for new logic. The `SongRepository` now loads these solely via the `MediaSourceTags` junction.
