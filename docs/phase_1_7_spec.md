# Phase 1.7 M2M Batch Hydration Spec

## Objective
Hydrate `Song` objects with their associated `Albums` and `Tags` with zero N+1 query penalties, adhering to the standard multi-selection "batch hydration" constraint established for `SongCredits`.

## 1. domain.py Updates
**Models to Add:**
- `Tag`: Represents a taxonomy term (`id`, `name`, `category`).
- `SongAlbum`: A bridge entity mapping a song to an album, containing the album metadata alongside the track numbers (`source_id`, `album_id`, `album_title`, `album_type`, `release_year`, `track_number`, `disc_number`, `is_primary`).
- Update `Song` model to include `albums: List[SongAlbum] = []` and `tags: List[Tag] = []`.

## 2. Repositories
**SongAlbumRepository (`src/data/song_album_repository.py`)**
- `get_albums_for_songs(song_ids: List[int]) -> List[SongAlbum]`
- Executes a `JOIN` across `SongAlbums` and `Albums` to yield a flat list of `SongAlbum` domain objects.

**TagRepository (`src/data/tag_repository.py`)**
- `get_tags_for_songs(song_ids: List[int]) -> List[Tuple[int, Tag]]` (or a `SongTag` bridging object)
- Executes a `JOIN` across `MediaSourceTags` and `Tags` to yield a flat list associating a `source_id` with a `Tag`. Let's create `MediaSourceTag` model or just return the relationship.

## 3. CatalogService Updates
- Define `tags: List[Tag]` and `albums: List[SongAlbum]` back onto the `Song` domain context.
- Update `CatalogService._hydrate_songs` to perform batched `get_albums_for_songs` and `get_tags_for_songs`, grouping the results and appending them to the respective songs.

## 4. Tests & Schema
- Update `schema.py` to include `Albums`, `SongAlbums`, `Tags`, `MediaSourceTags`.
- Update `test_repositories.py` to verify the batch fetching correctly maps M2M entities to Songs, including secondary attributes like `track_number` and `tag_category`.
