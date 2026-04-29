# Refactor Entity Repertoire to Use Slim Views

## Problem
Entity detail pages (Album, Artist, Publisher, Tag) display song repertoire using `renderSongList()` from utils.js, which:
1. Pulls full `SongView` objects (all credits, publishers, albums, tags hydrated)
2. Displays only 5 fields: title, artist, duration, BPM, is_active toggle
3. The is_active toggle doesn't actually work in this context (vestigial)
4. This forces `SongView` to maintain `display_artist` method only for rendering support
5. Unnecessary DB hydration cost

## Root Cause
`renderSongList()` was ported from V1 frontend without considering that V2 uses slim views everywhere else. Search/Filter already do slim correctly with their own renderers.

## Solution
Create a slim-specific song list renderer and update 4 entity detail endpoints to use `SongSlimView` instead of `SongView`.

## Changes Required

### Backend
1. **PublisherRepository**: Already has `get_song_ids_by_publisher()` → need to create slim variant OR change LibraryService to use search_slim pattern
2. **AlbumRepository**: Check if slim fetch exists
3. **IdentityRepository**: Check if slim fetch exists  
4. **TagRepository**: Check if slim fetch exists
5. Update LibraryService methods:
   - `get_songs_by_publisher()` → return slim
   - `get_songs_by_album()` → return slim
   - `get_songs_by_identity()` → return slim (artist detail)
   - `get_songs_by_tag()` → return slim
6. Update 4 CatalogRouter endpoints:
   - `/publishers/{id}/songs` → `response_model=List[SongSlimView]`
   - `/albums/{id}/songs` → `response_model=List[SongSlimView]`
   - `/artists/{id}/songs` → `response_model=List[SongSlimView]`
   - `/tags/{id}/songs` → `response_model=List[SongSlimView]`

### Frontend
1. Create new renderer: `renderSongListSlim()` in utils.js or songs.js
   - Remove toggle switch entirely
   - Keep: title, artist, duration, BPM
   - No is_active/can_activate fields needed
2. Update 4 entity detail renderers:
   - album_detail (albums.js)
   - artist_detail (artists.js)
   - publisher_detail (publishers.js)
   - tag_detail (tags.js)
   - Switch from `renderSongList()` to `renderSongListSlim()`

### Cleanup
1. Remove `is_active` rendering from `renderSongListSlim()`
2. Once confirmed no other code uses `display_artist`, remove from `SongView`
3. Remove `display_artist` hydration from service layer

## Verification
- Check what calls `SongView.display_artist` after removal attempt
- Ensure slim data has all 5 fields being rendered: display_title, display_artist, formatted_duration, bpm, (no toggle)
- Test all 4 entity detail pages render correctly

## Open Questions
- Do slim views already have all the fields needed, or need to modify SongSlimView?
- What's the pattern in search_slim to understand how to fetch slim for these endpoints?
- Should we remove the toggle completely or just disable it in entity context?
