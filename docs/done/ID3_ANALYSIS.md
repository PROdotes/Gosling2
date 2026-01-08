---
tags:
  - layer/core
  - domain/audio
  - status/done
  - type/reference
links: []
---
# ID3 Metadata & Logic Analysis

This document provides a detailed breakdown of ID3 data manipulation in the legacy Java Controller (`SongController.java`) compared to the current Python `MetadataService.py` implementation.

## 1. ID3 Data Handling Comparison

The following table details every ID3 field interacted with by the Java code and the current Python project.

| Field / Concept | Java (`SongController.java`) | ID3 Frame (Standard) | Python (`MetadataService.py`) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Artist / Performers** | `textArtist` | `TPE1` | `performers` | ✅ Matched |
| **Title** | `textTitle` | `TIT2` | `title` | ✅ Matched |
| **Composer** | `textComposer` | `TCOM` | `composers` | ✅ Matched |
| **Year** | `textYear` | `TYER` / `TDRC` | `recording_year` | ✅ Matched (Python parses both) |
| **Recording Date** | Reads as fallback for Year | `TDRC` | `recording_year` | ✅ Matched |
| **Album** | `textAlbum` | `TALB` | *Missing* | ❌ **Missing in Python** |
| **Publisher** | `textPublisher` | `TPUB` | *Missing* | ❌ **Missing in Python** |
| **Genre** | `dropGenre` | `TCON` | *Missing* | ❌ **Missing in Python** |
| **ISRC** | `textISRC` | `TSRC` | `isrc` | ✅ Matched |
| **Done / Key** | `checkDone` (Uses `TKEY`) | `TKEY` (Initial Key) | *Missing* | ❌ **Missing in Python** |
| **Duration** | Writes to `LENGTH` | `TLEN` | `duration` (Reads stream info) | ⚠️ Python reads audio stream, Java saves to tag |
| **BPM** | *Unused* | `TBPM` | `bpm` | ℹ️ Python Exclusive |
| **Lyricists** | *Unused* | `TOLY` / `TEXT` | `lyricists` | ℹ️ Python Exclusive |
| **Producers** | *Unused* | `TIPL` / `TXXX:PRODUCER` | `producers` | ℹ️ Python Exclusive |
| **Groups** | *Unused* | `TIT1` | `groups` | ℹ️ Python Exclusive |

### Critical Legacy Logic: The "Done" Flag
The Java application re-purposes the **Initial Key (`TKEY`)** frame to store a custom application state:
*   **"Done" (Processed)**: Writes the string `"true"`.
*   **"Not Done"**: Writes a single space `" "`.

#### Migration Strategy (Transition Protocol)
To modernize without breaking the active legacy app, Gosling2 will implement a **Dual-Mode** approach:

1.  **The New Standard**: Use a custom user-defined text frame `TXXX:GOSLING_DONE` (Value: `"1"` or `"0"`).
2.  **Read Logic**:
    *   Check `TXXX:GOSLING_DONE` first.
    *   If missing, fallback to `TKEY`. (If `TKEY` == `"true"`, status is Done).
3.  **Write Logic (Legacy Compatibility Mode)**:
    *   **Always** write the new `TXXX:GOSLING_DONE` frame.
    *   **If Legacy Mode is ACTIVE (Default)**: Mirror the status to `TKEY` (write `"true"` or `" "`).
        *   (Flag controlled via `settings.json`: `"legacy_compatibility_mode": true`).
    *   **If Legacy Mode is OFF (Future)**: Do NOT write to `TKEY`. Ideally, sanitize `TKEY` if it contains legacy values, but preserve it if it contains real musical key data (e.g. "Am", "12B").

3.  **New Metadata Validation Rules**:
    *   **Album**: REQUIRED. If missing/single, default to `"{Title} (Single)"`.
    *   **Publisher**: REQUIRED.
    *   **Genre**: REQUIRED.
    *   **Enforcement**: Use `completeness_criteria.json` to prevent marking as "Done" if these are empty.

## 2. Java Application Logic

### File Renaming & Organization
The Java controller enforces a strict directory structure in `updateMP3` -> `renameFile` -> `generateNewFilename`.

**Pattern**: `Z:\Songs\<GENRE>[\<YEAR>]\<ARTIST> - <TITLE>.mp3`

1.  **Sanitization**:
    *   Replaces `:` and `/` with `_`.
2.  **Genre-Based Routing**:
    *   `pop` -> Root folder (empty genre path).
    *   `domoljubne` -> `cro\domoljubne`.
    *   `acoustic` -> `akustika`.
    *   `club` -> `clubbing`.
3.  **Year Folder Logic**:
    *   **Standard**: Most genres include a Year subfolder (e.g., `house\2023\`).
    *   **Exceptions (Flat Structure)**: The following genres **skip** the year folder:
        *   `religiozne`, `oldies`, `x-mas`, `cro\domoljubne`, `country`, `slow`, `metal`, `navijacke`, `rock`, `jazz`, `dance`, `trance`, `electronic`, `acoustic`, `funk`, `blues`.

### Metadata Cleaning (On Save)
When `updateMP3` is called (Ctrl+S):
1.  **Title/Artist Cleanup**:
    *   Moves `(ft X)` from **Title** to **Artist**.
    *   Moves `(With X)` from **Title** to **Artist**.
    *   Replaces `(i)` at the end of **Title** with `(Instrumental)`.
2.  **Croatian Char Replacement**:
    *   Calls `replaceCroChars` on Artist, Title, Album, Publisher, and Composer.

## 3. Python Project Current Capabilities
*   **Reading**: Robustly reads Artist, Title, Composer, Year (and Recording Date), BPM, Lyricists, Producers, Groups, and ISRC.
*   **Missing**: Does not currently read/write Album, Publisher, Genre, or the critical `TKEY` (Done) flag.
*   **Writing**: "Export to File" UI is implemented but logic is stubbed. "Import from File" is fully implemented.
