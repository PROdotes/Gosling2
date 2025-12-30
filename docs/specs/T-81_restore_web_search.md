# T-81 Restore Web Search & Settings

## Objective
Restore the "Web Search" workflow feature that was lost during previous refactors. This allows the user to quickly verify metadata via external providers (Google, MusicBrainz, Spotify, etc.) directly from the editor.

## Features Restored (Partial)
1.  **Search Button**: Added "WEB" button to the `SidePanelWidget` footer (next to Ready button).
2.  **Context Menu**: Right-clicking the button allows switching the Search Provider (defaut: Google).
3.  **Providers**:
    - Google
    - Spotify
    - YouTube
    - Discogs
    - MusicBrainz (with Smart Query: `artist:"..." AND recording:"..."`)
4.  **Logic**: 
    - **Tag Lookup (Revised)**: Instead of the Search API, use the `taglookup` endpoint which is purpose-built for file tagging.
    - **Endpoint**: `https://musicbrainz.org/taglookup/index`
    - **Parameters**: 
        - `tag-lookup.artist`: Artist Name
        - `tag-lookup.track`: Song Title
        - `tag-lookup.release`: Album Name (if available)
        - `tag-lookup.duration`: Duration in ms (if available)
    - **Advantage**: Handles special characters (like `/`) natively via standard URL encoding, avoiding Lucene syntax issues entirely.

## Missing Functionality (To Be Restored)
- **Settings Manager**: Restored. The "Settings Window" now includes a "SEARCH PROVIDER" dropdown, and the right-click menu on the search button persists the selection to `SettingsManager`.
- **Persistent Storage**: `KEY_SEARCH_PROVIDER` added to `SettingsManager` to save the selected `_search_provider`.
- **Lucene Sanitization**: Addressed by switching to the MusicBrainz `taglookup` endpoint, which handles standard URL encoding for special characters.


## Test Plan
1.  Select a song.
2.  Click "WEB" button. Verify it opens Google with "Artist Title".
3.  Right-click "WEB" -> Select "MusicBrainz".
4.  Click "WEB" again. Verify it opens MusicBrainz with specific `artist:` query.

## Next Steps
- None. Task Complete.
