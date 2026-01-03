# ⚙️ Settings Audit

This document tracks the mapping between `SettingsManager` keys and the user-facing `SettingsDialog`.

## ✅ 1. Currently Implemented in Settings Dialog
These are the settings visible and editable in the current UI (including the recently added File Management section).

| Section | Label | Underlying Key | Description |
| :--- | :--- | :--- | :--- |
| **Library** | Root Directory | `KEY_ROOT_DIRECTORY` | Base folder for music scanning. |
| **File Management** | Enable Auto-Renaming | `KEY_RENAME_ENABLED` | **[New]** Master switch for renaming logic. |
| **File Management** | Move Files on 'Done' | `KEY_MOVE_AFTER_DONE` | **[New]** Move file from Inbox to Artist folder when marked Done. |
| **File Management** | Pattern | `KEY_RENAME_PATTERN` | **[New]** Template: `{Artist}/{Album}/{Title}` |
| **Transcoding** | MP3 Quality | `KEY_CONVERSION_BITRATE` | e.g., "320k", "VBR". |
| **Transcoding** | FFmpeg Path | `KEY_FFMPEG_PATH` | Path to `ffmpeg.exe`. |
| **Metadata** | Search Provider | `KEY_SEARCH_PROVIDER` | Default engine (Google, Spotify, etc.) for `Ctrl+Click`. |
| **Metadata** | Default Year | `KEY_DEFAULT_YEAR` | Auto-fill year for new items (0 = Empty). |

---

## ❓ 2. Missing (Potential Candidates)
These keys exist in `SettingsManager` but have **no UI** in the Settings Dialog.

| Category | Key | Current Behavior | Should we add it? |
| :--- | :--- | :--- | :--- |
| **Playback** | `KEY_CROSSFADE_ENABLED` | Toggled via Right Panel Footer (temp?). | Maybe a global default? |
| **Playback** | `KEY_CROSSFADE_DURATION` | Selected in Right Panel Footer (temp?). | Maybe a global default selection? |
| **Conversion** | `KEY_CONVERSION_ENABLED` | Logic exists, but no "Master Switch". | Currently assumed enabled if FFmpeg path is set? |
| **Library** | `KEY_DATABASE_PATH` | Hardcoded/Internal default (`.gosling2.db`). | **Advanced**: Allow moving the DB? |

---

## 🙈 3. Internal / Hidden (Correctly Excluded)
These store UI state and do not belong in a configuration dialog.

| Category | Key | Reason to Hide |
| :--- | :--- | :--- |
| **Window** | `KEY_WINDOW_GEOMETRY` | Restores window position/size. |
| **Window** | `KEY_MAIN_SPLITTER_STATE` | Restores panel sizes. |
| **Window** | `KEY_RIGHT_PANEL_WIDTH_*` | **[New]** Remembers width for Editor vs Normal mode. |
| **Library** | `KEY_LIBRARY_LAYOUTS` | Remembers column order/visibility. |
| **Library** | `KEY_LAST_IMPORT_DIRECTORY` | Convenience for file dialogs. |
| **Library** | `KEY_TYPE_FILTER` | Remembers selected tab (All/Single/EP). |
| **Playback** | `KEY_VOLUME` | Remembers volume slider position. |
| **Playback** | `KEY_LAST_PLAYLIST` | Restores session on restart. |
