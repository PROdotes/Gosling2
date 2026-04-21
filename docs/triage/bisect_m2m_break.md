# Bisect Plan: M2M ID Regression

## The Problem

Selecting a specific entity from a search dropdown (Publisher, Tag, or Credit) occasionally results in the wrong entity being linked to the song/album.

- **Known Regressions**:
  - Tag: "Cro" -> "Pop"
  - Publisher: "Atlantic Outpost" -> "Dancing Bear"
- **Working as Intended**:
  - Genre mappings (seem stable)
- Symptom: Temporary fix with `LOWER()` in repository name-lookups resolved some issues, implying a case-sensitivity collision.
- Root Cause Hypothesis: Backend services (`EditService` and `Repositories`) are discarding the `id` passed from the frontend and falling back to name-based `get_or_create` lookups.

## Affected Components

- `src/services/edit_service.py` -> `add_song_publisher`, `add_song_tag`, etc.
- `src/data/publisher_repository.py` -> `add_song_publisher` (ignores ID)
- `src/data/tag_repository.py` -> `add_tag` (ignores ID)
- `src/data/song_credit_repository.py` -> `add_credit` (has ID but fallbacks to name)

## Tomorrow's Protocol

1. **Define Test Case**:
   - Seed database with "Atlantic Outpost" (ID: X).
   - Attempt to add publisher to a song using ID: X but `publisher_name="atlantic outpost"` (lowercase).
   - If ID is ignored and lookup is case-sensitive, it may create a duplicate or fail.
2. **Verify Failure**: Remove the `LOWER` workaround from `PublisherRepository` and `TagRepository`.
3. **Git Bisect**:
   - `git bisect start`
   - `git bisect bad HEAD`
   - `git bisect good <commit_from_last_week>`
   - Goal: Find the commit where `add_song_publisher` stopped prioritizing the `publisher_id`.

## Resolution Goal

Update all `Repository.add_*` methods to be "ID-First":

```python
def add_entity(self, song_id, name, entity_id=None):
    if entity_id:
        # Link directly by ID
    else:
        # Fallback to get_or_create (Name-based)
```
