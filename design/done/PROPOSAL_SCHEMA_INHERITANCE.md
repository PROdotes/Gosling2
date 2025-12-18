# Architectural Proposal: Schema Inheritance Model (v5 — Simplified)

## Problem
The current `Files` table stores all audio items with identical columns. But:
- **Songs** need BPM, ISRC, timing fields (Intro, Outro, Cue points)
- **Commercials** need Campaign links
- **Streams** need URL, failover
- Jingles/VoiceTracks/Recordings are just types, no special fields

## Solution: Flat Inheritance (No Files Layer)

```
┌─────────────────────────────────────────────────────────────┐
│                      MediaSources                           │
│  (SourceID, TypeID, Name, Path/URL, Duration, Notes)        │
│                Base for ALL playable items                  │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌───────────┐          ┌─────────┐
   │  Songs  │          │Commercials│          │ Streams │
   │ Timing, │          │ Campaign  │          │Failover │
   │ BPM,ISRC│          │           │          │ Bitrate │
   └─────────┘          └───────────┘          └─────────┘

Jingles, VoiceTracks, Recordings = just TypeID markers (no extra table)
```

---

## Core Tables

### 1. Types (Lookup)
```sql
CREATE TABLE Types (
    TypeID INTEGER PRIMARY KEY,
    TypeName TEXT NOT NULL UNIQUE
);

INSERT INTO Types VALUES
    (1, 'Song'),
    (2, 'Jingle'),
    (3, 'Commercial'),
    (4, 'VoiceTrack'),
    (5, 'Recording'),
    (6, 'Stream');
```

### 2. MediaSources (Base for All)
```sql
CREATE TABLE MediaSources (
    SourceID INTEGER PRIMARY KEY,
    TypeID INTEGER NOT NULL,
    Name TEXT NOT NULL,
    Notes TEXT,                  -- Searchable description
    Source TEXT NOT NULL,        -- Path (C:\...), URL (https://...), or network path
    Duration REAL,               -- Actual duration in seconds (NULL for streams)
    IsActive BOOLEAN DEFAULT 1,
    FOREIGN KEY (TypeID) REFERENCES Types(TypeID)
);
```

---

## Type-Specific Tables

### 3. Songs (Music-Specific)
```sql
CREATE TABLE Songs (
    SourceID INTEGER PRIMARY KEY,
    -- Music metadata
    TempoBPM INTEGER,
    RecordingYear INTEGER,
    ISRC TEXT,
    IsDone BOOLEAN DEFAULT 0,
    -- Timing fields (only Songs have these)
    CueIn REAL DEFAULT 0,        -- Playback start trim
    CueOut REAL,                 -- Playback end trim
    Intro REAL,                  -- End of talk-over zone at start
    Outro REAL,                  -- Start of talk-over zone at end
    HookIn REAL,                 -- Best teaser segment start
    HookOut REAL,                -- Best teaser segment end
    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE
);
```

### 4. Streams (Remote Audio)
```sql
CREATE TABLE Streams (
    SourceID INTEGER PRIMARY KEY,
    FailoverURL TEXT,            -- Backup stream if primary fails
    StreamFormat TEXT,           -- 'MP3', 'AAC', 'FLAC'
    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE
);
```

### 5. Commercials (Ad-Specific)
```sql
CREATE TABLE Commercials (
    SourceID INTEGER PRIMARY KEY,
    CampaignID INTEGER,
    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE,
    FOREIGN KEY (CampaignID) REFERENCES Campaigns(CampaignID) ON DELETE SET NULL
);
```

*Note: Jingles, VoiceTracks, Recordings have no extra fields — just a TypeID in MediaSources.*

---

## Business Tables

### 6. Agencies
```sql
CREATE TABLE Agencies (
    AgencyID INTEGER PRIMARY KEY,
    Name TEXT NOT NULL UNIQUE,
    ContactName TEXT,
    ContactEmail TEXT,
    ContactPhone TEXT
);
```

### 7. Clients
```sql
CREATE TABLE Clients (
    ClientID INTEGER PRIMARY KEY,
    AgencyID INTEGER,
    Name TEXT NOT NULL UNIQUE,
    ContactName TEXT,
    ContactEmail TEXT,
    ContactPhone TEXT,
    Notes TEXT,
    FOREIGN KEY (AgencyID) REFERENCES Agencies(AgencyID) ON DELETE SET NULL
);
```

### 8. Campaigns
```sql
CREATE TABLE Campaigns (
    CampaignID INTEGER PRIMARY KEY,
    ClientID INTEGER NOT NULL,
    CampaignName TEXT NOT NULL,
    StartDate DATE,
    EndDate DATE,
    RequestedPlays INTEGER,
    ScheduleNotes TEXT,
    Notes TEXT,
    FOREIGN KEY (ClientID) REFERENCES Clients(ClientID) ON DELETE CASCADE
);
```

---

## Tags (Unified)

All categorization uses Tags. Mandatory requirements enforced in code (completeness_criteria.json).

### 9. Tags
```sql
CREATE TABLE Tags (
    TagID INTEGER PRIMARY KEY,
    TagName TEXT NOT NULL,
    Category TEXT,              -- 'Genre', 'Language', 'Mood', 'Usage', or NULL
    UNIQUE(TagName, Category)
);

CREATE TABLE MediaSourceTags (
    SourceID INTEGER NOT NULL,
    TagID INTEGER NOT NULL,
    PRIMARY KEY (SourceID, TagID),
    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE,
    FOREIGN KEY (TagID) REFERENCES Tags(TagID) ON DELETE CASCADE
);

-- Hierarchical tag relations (1980s contains 1987, Rock contains Classic Rock)
CREATE TABLE TagRelations (
    ParentTagID INTEGER NOT NULL,
    ChildTagID INTEGER NOT NULL,
    PRIMARY KEY (ParentTagID, ChildTagID),
    FOREIGN KEY (ParentTagID) REFERENCES Tags(TagID) ON DELETE CASCADE,
    FOREIGN KEY (ChildTagID) REFERENCES Tags(TagID) ON DELETE CASCADE
);

-- Auto-tagging rules (Beatles → Oldies, RecordingYear 1960-1969 → 1960s)
CREATE TABLE AutoTagRules (
    RuleID INTEGER PRIMARY KEY,
    TargetTagID INTEGER NOT NULL,   -- Tag to apply when rule matches
    RuleType TEXT NOT NULL,         -- 'FIELD', 'TAG', 'CONTRIBUTOR'
    -- For FIELD rules
    FieldName TEXT,                 -- 'RecordingYear', 'TempoBPM', etc.
    Operator TEXT,                  -- 'BETWEEN', '=', '<', '>', 'LIKE'
    Value1 TEXT,
    Value2 TEXT,                    -- For BETWEEN
    -- For TAG/CONTRIBUTOR rules
    SourceTagID INTEGER,            -- If has this tag, apply TargetTag
    ContributorID INTEGER,          -- If has this artist, apply TargetTag
    FOREIGN KEY (TargetTagID) REFERENCES Tags(TagID) ON DELETE CASCADE,
    FOREIGN KEY (SourceTagID) REFERENCES Tags(TagID) ON DELETE SET NULL,
    FOREIGN KEY (ContributorID) REFERENCES Contributors(ContributorID) ON DELETE SET NULL
);
```

**Mandatory Tags (enforced in code):**
- Songs require at least 1 tag with `Category = 'Genre'`
- Songs require at least 1 tag with `Category = 'Language'` (including "Instrumental")

**Built-in Categories:**
| Category | Examples | Mandatory |
|----------|----------|-----------|
| Genre | Rock, Pop, Jazz | Yes (Songs) |
| Language | English, Croatian, Instrumental | Yes (Songs) |
| Mood | Upbeat, Mellow | No |
| Usage | Morning, Ad-break | No |
| *(NULL)* | Custom user tags | No |

**AutoTagRules Implementation Notes:**
- **Execution order:** FIELD rules → TAG rules → CONTRIBUTOR rules
- **Cascading:** Rules can trigger other rules (intentional)
- **Cycle detection:** App must detect and break infinite loops
- **Rule visualization:** UI should show rule graph (see wishlist)

---

## Playlists

### 12. Playlists
```sql
CREATE TABLE Playlists (
    PlaylistID INTEGER PRIMARY KEY,
    Name TEXT NOT NULL,
    Description TEXT,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE PlaylistItems (
    PlaylistItemID INTEGER PRIMARY KEY,
    PlaylistID INTEGER NOT NULL,
    SourceID INTEGER NOT NULL,
    Position INTEGER NOT NULL,
    FOREIGN KEY (PlaylistID) REFERENCES Playlists(PlaylistID) ON DELETE CASCADE,
    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE
);
```

---

## Audit & Recovery

### 13. ChangeLog
```sql
CREATE TABLE ChangeLog (
    LogID INTEGER PRIMARY KEY,
    TableName TEXT NOT NULL,
    RecordID INTEGER NOT NULL,
    FieldName TEXT NOT NULL,
    OldValue TEXT,
    NewValue TEXT,
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    BatchID TEXT
);
```

### 14. DeletedRecords
```sql
CREATE TABLE DeletedRecords (
    DeleteID INTEGER PRIMARY KEY,
    TableName TEXT NOT NULL,
    RecordID INTEGER NOT NULL,
    FullSnapshot TEXT NOT NULL,
    DeletedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    RestoredAt DATETIME,
    BatchID TEXT
);
```

---

## Existing Tables (Retained)

### 15. Contributors & Roles
```sql
-- Contributors, Roles, GroupMembers unchanged
-- Junction links to MediaSources

CREATE TABLE MediaSourceContributorRoles (
    SourceID INTEGER NOT NULL,
    ContributorID INTEGER NOT NULL,
    RoleID INTEGER NOT NULL,
    PRIMARY KEY (SourceID, ContributorID, RoleID),
    FOREIGN KEY (SourceID) REFERENCES MediaSources(SourceID) ON DELETE CASCADE,
    FOREIGN KEY (ContributorID) REFERENCES Contributors(ContributorID) ON DELETE CASCADE,
    FOREIGN KEY (RoleID) REFERENCES Roles(RoleID) ON DELETE CASCADE
);

-- Aliases for artist search (P!nk = Pink = Alecia Moore)
CREATE TABLE ContributorAliases (
    AliasID INTEGER PRIMARY KEY,
    ContributorID INTEGER NOT NULL,
    AliasName TEXT NOT NULL,
    FOREIGN KEY (ContributorID) REFERENCES Contributors(ContributorID) ON DELETE CASCADE
);
```

### 16. Publishers & Albums
```sql
-- Publishers, AlbumPublishers unchanged

-- Albums with type categorization
CREATE TABLE Albums (
    AlbumID INTEGER PRIMARY KEY,
    Title TEXT NOT NULL,
    AlbumType TEXT,              -- 'Single', 'EP', 'Album', 'Compilation', 'Live', 'Soundtrack', etc.
    ReleaseYear INTEGER,
    -- Other fields unchanged
    FOREIGN KEY (PublisherID) REFERENCES Publishers(PublisherID)
);

-- Junction links to Songs only
CREATE TABLE SongAlbums (
    SourceID INTEGER NOT NULL,
    AlbumID INTEGER NOT NULL,
    TrackNumber INTEGER,          -- Position on album
    PRIMARY KEY (SourceID, AlbumID),
    FOREIGN KEY (SourceID) REFERENCES Songs(SourceID) ON DELETE CASCADE,
    FOREIGN KEY (AlbumID) REFERENCES Albums(AlbumID) ON DELETE CASCADE
);
```

**Enforcement (in code):**
- Albums must have at least 1 song in SongAlbums
- When removing last song: Ask "Delete album or keep empty?" (user might be fixing mistakes)

---

## Summary: All Tables

| # | Table | Purpose |
|---|-------|---------|
| 1 | Types | Lookup: Song, Jingle, Commercial, etc. |
| 2 | MediaSources | Base for all playable items (Source path/URL) |
| 3 | Songs | Music-specific (BPM, ISRC, timing) |
| 4 | Streams | Stream-specific (Failover, Format) |
| 5 | Commercials | Ad-specific (CampaignID) |
| 6 | Agencies | Ad agencies |
| 7 | Clients | Advertisers |
| 8 | Campaigns | Ad campaigns |
| 9 | Tags + MediaSourceTags | All categorization (Genre, Language, Mood, custom) |
| 10 | TagRelations | Hierarchical tags (1980s → 1987) |
| 11 | AutoTagRules | Smart auto-tagging rules |
| 12 | Playlists + PlaylistItems | Saved playlists |
| 13 | ChangeLog | Audit trail |
| 14 | DeletedRecords | Deletion recovery |
| 15 | Contributors + Roles + Junction | Artists, composers |
| 16 | ContributorAliases | Artist name variants (P!nk = Pink) |
| 17 | Publishers + Albums + SongAlbums | Labels, albums (with TrackNumber) |

**Total: 25 tables** (when counted individually with junctions)

---

## What Changed from v4

| Before (v4) | After (v5) |
|-------------|------------|
| MediaSources → Files → Songs | MediaSources → Songs |
| Separate Genres + Languages tables | Unified Tags with Category |
| Path + URL columns | Single Source field |
| Category column in Types | Removed |
| No auto-tagging | AutoTagRules table |
| 22 tables | 20 tables |

**Simplified:** Fewer tables, unified tagging, smarter auto-tagging.

---

## Checklist
- [ ] Finalize schema with user
- [ ] Update DATABASE.md
- [ ] Create migration script
- [ ] Update repositories
- [ ] Update models
- [ ] Update tests
