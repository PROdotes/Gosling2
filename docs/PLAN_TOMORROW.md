# Plan: v3core Phase 2 - Completing Retrieval Context

## Objective
Finalize the "Read" side of the Catalog. A Song is not fully retrieved until it knows its Album and its Tags (Genre).

## 1. Tag Hydration (Genre/Mood)
- **Data**: Create `TagRepository` to retrieve strings from `Tags` and `SongTags` tables.
- **Domain**: Add `tags: list[str]` to the `Song` model.
- **Service**: `CatalogService.get_song` must fetch and attach these tags.

## 2. Album Hydration
- **Data**: Create `AlbumRepository` to fetch Album metadata.
- **Service**: Link the `Song.album_id` to a hydrated `Album` object.

## 3. Verification
- Expand `tests/v3core/test_catalog.py` to ensure high-fidelity retrieval of these new fields.
- Zero-tolerance for unused imports or linting errors.

*Note: No Add/Update/Delete until we have a UI to drive them. We walk before we run.*
