# Spotify Credits Ingest — Implementation Spec

**Date:** 2026-03-31  
**Status:** Ready for review

---

## Overview

Allow users to paste raw text from Spotify's "Credits" panel directly into the song detail view. The app parses it, shows a preview, and writes credits + publishers using existing endpoints.

---

## Input Format

Spotify credits copy-paste produces plain text in this structure:

```
Credits
<Song Title>
Artist

<Section Heading>
<Person Name>
<Role> • <Role> • <Role>

Sources
<Publisher1>/<Publisher2>
```

**Key observations:**
- Line 1 is always `Credits` (discard)
- Line 2 is the song title — use for mismatch check only
- `Artist` line after the title — always skip (performers don't copy from Spotify's special div)
- Section headings (`Composition & Lyrics`, `Production & Engineering`, `Performers`, etc.) — **ignore**, roles come from the person's sub-lines
- Role lines use `•` (bullet) as delimiter — split and trim each
- `Sources` section — publishers are `/`-delimited on a single line

---

## Parser Rules

```
State machine, line by line:

1. Skip "Credits" header
2. Capture line 2 as `parsed_title`
3. Skip "Artist" line
4. On blank line — reset current_name
5. On a line with no • and not a known section heading → it's a person's name → set current_name
6. On a line containing • → it's a role line → split on •, strip, emit (current_name, role) per role
7. On a line that is a known section heading → track that we're in that section (only matters for Sources)
8. In Sources section: a non-blank line → split on / → emit each as publisher
```

**Known section headings to detect:**
- `Composition & Lyrics`
- `Production & Engineering`
- `Performers`
- `Sources`
- Any other heading not matching above — treat same as Composition (has name + role lines)

**Role matching:**
- Roles are written as-is from Spotify (e.g. `Composer`, `Lyricist`, `Arranger`, `Producer`, `Background Vocals`)
- Pass directly to `SongCreditRepository` — `get_or_create_role` handles new roles gracefully
- No mapping/normalization needed

---

## Backend

### New endpoint: Parse only (no writes)

```
POST /api/v1/songs/{song_id}/spotify-credits/parse
Body: { "raw_text": "..." }
```

**Returns:**
```json
{
  "parsed_title": "Bezuvjetno",
  "title_match": true,
  "credits": [
    { "name": "Goran Boskovic", "role": "Composer" },
    { "name": "Goran Boskovic", "role": "Lyricist" },
    { "name": "Goran Boskovic", "role": "Arranger" },
    { "name": "Željko Nikolin", "role": "Arranger" },
    { "name": "Goran Boskovic", "role": "Producer" },
    { "name": "Željko Nikolin", "role": "Producer" }
  ],
  "publishers": ["Menart"]
}
```

`title_match` is a **case-insensitive** comparison between `parsed_title` and the song's current `MediaName`. Frontend uses this for the warning badge — never blocks submission.

**Router:** Add to `src/engine/routers/catalog.py` or a new `src/engine/routers/spotify.py` — TBD.  
**No new service method needed** — pure parsing logic, no DB writes in this endpoint.

### Writes use existing endpoints

After user confirms in the preview UI, the frontend fires existing endpoints:

- `POST /api/v1/songs/{song_id}/credits` — `{ "display_name": "...", "role_name": "..." }` — one per credit row
- `POST /api/v1/songs/{song_id}/publishers` — `{ "publisher_name": "..." }` — one per publisher

---

## Frontend

### Entry point
A button in the song detail view (credits section area) — "Import from Spotify" — opens a modal.

### Modal layout (two-panel, matches existing screenshot style)

```
+------------------------------------------+
| Import Spotify Credits for: <Song Title> |
+------------------------------------------+
| [warning badge if title mismatch]         |
|                                           |
| PASTE TEXT          | PREVIEW & MAP       |
| +----------------+  | +----------------+ |
| | <textarea>     |  | | Name  | Roles  | |
| |                |  | | ...   | ...    | |
| +----------------+  | +----------------+ |
|                      | [Import] [Cancel]  |
+------------------------------------------+
```

### Behavior

1. User pastes text → auto-parse fires (on `input` event, debounced ~300ms)
2. If `title_match` is false → show yellow warning: `"Spotify title: '<parsed_title>'" ` — don't block
3. Preview panel renders rows:
   - Each row: **Name pill** | **Role chip(s)** | `+` button (add role) | `×` button (remove row)
   - Publishers render with role chip labeled `Publisher`
4. User can edit/remove rows before importing
5. **Import** button → fires `POST /credits` and `POST /publishers` sequentially for all rows → closes modal → refreshes song detail

### Files to touch

- `src/static/js/dashboard/` — new `components/spotify_modal.js`
- `src/templates/dashboard.html` — add modal scaffold + trigger button
- `src/engine/routers/catalog.py` (or new `spotify.py`) — parse endpoint
- `src/engine_server.py` — register router if new file

---

## Edge Cases

| Scenario | Handling |
|---|---|
| Title mismatch | Yellow warning badge, import not blocked |
| Role not in DB | `get_or_create_role` creates it automatically |
| Publisher already linked | `INSERT OR IGNORE` at DB level — safe to re-submit |
| Credit already linked | `UNIQUE(SourceID, CreditedNameID, RoleID)` constraint + `INSERT OR IGNORE` — idempotent |
| Empty paste | Parse returns empty arrays, preview shows nothing |
| Performers section | Parsed same as other sections — name + role lines |
| Multiple publishers | Split on `/` — e.g. `Menart/Croatia Records` → two entries |

---

## Out of Scope

- Artist identity linking (OwnerIdentityID) — left as NULL, same as manual credit entry
- Editing publisher names in the modal — use the existing publisher editor for corrections
- Batch import across multiple songs
