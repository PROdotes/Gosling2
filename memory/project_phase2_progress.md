---
name: Phase 2 CRUD Progress
description: Where we left off on Phase 2 Metabolic Updates (CRUD) implementation
type: project
---

Phase 2 backend data layer is complete. All repo methods written, tested, and lookup docs updated.

**Why:** Implementing CRUD for song metadata editing per PHASE_2_METABOLIC_UPDATES_SPEC.md

**How to apply:** Pick up at publisher CRUD tests, then song_album CRUD tests, then album CRUD tests, then service layer, then API endpoints.

## Completed
- `SongRepository.update_scalars()` — tested ✅
- `SongCreditRepository`: `get_or_create_role`, `get_or_create_credit_name`, `add_credit`, `remove_credit`, `update_credit_name` — tested ✅
- `TagRepository`: `get_or_create_tag`, `add_tag`, `remove_tag`, `update_tag` — tested ✅
- `PublisherRepository`: `get_or_create_publisher`, `add_song_publisher`, `remove_song_publisher`, `update_publisher` — written, NOT tested yet
- `SongAlbumRepository`: `add_album`, `remove_album`, `update_track_info` — written, NOT tested yet
- `AlbumRepository`: `create_album`, `update_album`, `add_album_credit`, `remove_album_credit`, `set_album_publisher` — written, NOT tested yet
- `SongCredit` domain model: added `credit_id` field
- `insert_credits`, `insert_tags`, `insert_song_publishers`, `_insert_album_credits` all refactored to use shared get-or-create helpers
- `docs/lookup/data.md` updated with all new methods
- Lookup integrity test passing, all 745 tests passing

## Key Decisions Made
- No separate ArtistRepository — credits are just name+role, artist is just a credit with Performer role
- `ArtistRepository` in the spec was hallucinated — `SongCreditRepository` owns `ArtistNames` already
- `AlbumRepository` already existed — spec was wrong about it being new
- Junction row removals are hard deletes (no IsDeleted on junction tables) — this is the existing pattern
- `add_credit` / `add_tag` / `add_song_publisher` return the entity for API use

## Completed (continued)
- `PublisherRepository`: `get_or_create_publisher`, `add_song_publisher`, `remove_song_publisher`, `update_publisher` — tested ✅
- `SongAlbumRepository`: `add_album`, `remove_album`, `update_track_info` — tested ✅
- `AlbumRepository`: `create_album`, `update_album`, `add_album_credit`, `remove_album_credit`, `set_album_publisher` — tested ✅
- Schema bug fixed: `AlbumCredits` was missing `UNIQUE(AlbumID, CreditedNameID, RoleID)` constraint in `schema.py` (existed in prod DB only)
- All 801 tests passing

## Completed (continued)
- `CatalogService` update methods: `update_song_scalars`, `add/remove_song_credit`, `update_artist_name`, `add/remove_song_album`, `create_and_link_album`, `update_song_album_link`, `update/add/remove album artist/publisher`, `add/remove_song_tag`, `update_tag`, `add/remove_song_publisher`, `update_publisher` — all written ✅
- `docs/lookup/services.md` updated ✅
- All 801 tests passing ✅

## Next Session
1. API endpoints: `src/routers/song_updates.py` — implement all PATCH/POST/DELETE endpoints per spec
   - Must register router in the app (check existing routers for pattern)
   - Follow TDD standard: status codes 200/400/404/422/500, exhaustive response shape assertions
   - Tests go in `tests/test_api/test_song_updates_api.py`

### Endpoint List
**Scalar:** `PATCH /api/songs/{song_id}`

**Credits:**
- `POST /api/songs/{song_id}/credits` — body: `{display_name, role_name}`
- `DELETE /api/songs/{song_id}/credits/{credit_id}`
- `PATCH /api/songs/{song_id}/credits/{name_id}` — body: `{display_name}` (global rename)

**Albums:**
- `POST /api/songs/{song_id}/albums` — body: `{album_id}` OR `{album_title, ...}` (create+link)
- `DELETE /api/songs/{song_id}/albums/{album_id}`
- `PATCH /api/songs/{song_id}/albums/{album_id}` — body: `{track_number, disc_number}`
- `PATCH /api/albums/{album_id}` — body: album fields (global update)
- `POST /api/albums/{album_id}/credits` — body: `{artist_name}`
- `DELETE /api/albums/{album_id}/credits/{name_id}`
- `PATCH /api/albums/{album_id}/publisher` — body: `{publisher_name}`

**Tags:**
- `POST /api/songs/{song_id}/tags` — body: `{tag_name, category}`
- `DELETE /api/songs/{song_id}/tags/{tag_id}`
- `PATCH /api/tags/{tag_id}` — body: `{tag_name, category}` (global update)

**Publishers:**
- `POST /api/songs/{song_id}/publishers` — body: `{publisher_name}`
- `DELETE /api/songs/{song_id}/publishers/{publisher_id}`
- `PATCH /api/publishers/{publisher_id}` — body: `{publisher_name}` (global rename)

## Key Facts for Next Session
- Service methods all exist and are tested (843 tests passing)
- `update_credit_name` not `update_artist_name` (was renamed)
- `add_album_credit` / `remove_album_credit` (not add/remove_album_artist)
- Album update dict key is `"title"` not `"album_title"`
- Check `src/engine/` for how existing routers are registered and how `CatalogService` is injected
