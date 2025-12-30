---
tags:
  - layer/data
  - layer/ui
  - domain/playlist
  - domain/database
  - status/planned
  - type/feature
  - size/large
links:
  - "[[DATABASE]]"
---
# Architectural Proposal: Saved Playlists

## Problem
Current app has no way to save a curated list of songs for reuse. If you spend 20 minutes building a "Friday Night Oldies" set, once it plays, it's gone.

## Features

### 1. Save Current Queue as Playlist
- Export entire queue (including already-played songs)
- Name the playlist
- Store in database

### 2. Load Playlist into Queue
- Insert before/after any song in current queue
- Or replace entire queue
- Preserve original playlist for reuse

### 3. Playlist Management
- View all saved playlists
- Edit (add/remove songs, reorder)
- Delete
- Duplicate

### 4. Import/Export
- Export to M3U/M3U8 (standard format)
- Import from M3U/M3U8
- Drag & drop M3U files

---

## Schema

### Playlists Table
```sql
CREATE TABLE Playlists (
    PlaylistID INTEGER PRIMARY KEY,
    Name TEXT NOT NULL,
    Description TEXT,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### PlaylistItems Junction
```sql
CREATE TABLE PlaylistItems (
    PlaylistID INTEGER NOT NULL,
    SourceID INTEGER NOT NULL,
    Position INTEGER NOT NULL,  -- Order in playlist
    PRIMARY KEY (PlaylistID, SourceID),
    FOREIGN KEY (PlaylistID) REFERENCES Playlists(PlaylistID),
    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID)
);
```

---

## UI Concepts

### Save Dialog
- Trigger: Button or Ctrl+S on queue
- Options: "Include played songs" checkbox (default: yes)
- Name field with autocomplete (overwrite existing?)

### Load Dialog
- List of saved playlists with song count
- Preview songs before loading
- Insert options: "Before selected", "After selected", "Replace all"

### Playlist Panel (optional)
- Sidebar section showing saved playlists
- Drag playlist onto queue to insert

---

## Checklist
- [ ] Create Playlists and PlaylistItems tables
- [ ] Add repository for playlist CRUD
- [ ] "Save Queue" button/action
- [ ] "Load Playlist" dialog
- [ ] M3U export
- [ ] M3U import
- [ ] Playlist management UI
