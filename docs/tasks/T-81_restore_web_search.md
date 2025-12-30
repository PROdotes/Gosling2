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
4.  **Logic**: Queries are constructed from the *Editor Fields* (what you see) rather than just the Database, allowing for correction-based searching.

## Missing Functionality (To Be Restored)
- **Settings Manager**: The original "Settings Window" and persistent storage for the default provider are missing. Currently, the provider resets to "Google" on restart.
- **Persistent Storage**: Need to hook up `QSettings` or a `SettingsService` to save the selected `_search_provider`.

## Test Plan
1.  Select a song.
2.  Click "WEB" button. Verify it opens Google with "Artist Title".
3.  Right-click "WEB" -> Select "MusicBrainz".
4.  Click "WEB" again. Verify it opens MusicBrainz with specific `artist:` query.

## Next Steps
- Implement `SettingsService` integration to persist the provider choice.
- Restore/Recreate the User Settings Dialog if needed.
