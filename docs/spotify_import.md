# Spotify Credits Import (Add Artist window)

## Purpose
Add a Paste/Import flow to the Add Artist window that parses Spotify-style credit blocks into structured artist entries with normalized roles and a preview for user confirmation.

## Goals
- Let users paste Spotify-credit text and quickly import artist names + roles.
- Provide a preview UI to correct names/roles before import.
- Normalize common role synonyms to app canonical roles while preserving unknown roles for manual mapping.
- Be robust to common formatting variants and noisy text.

## Architecture & Optimization

**KEY CONTEXT**: This feature is **always used while editing a song** (due to role context). Duplicates are impossible since each artist+role combination is unique. After import, the artist editor closes with data added the same way as single entries.

**OPTIMIZATION**: Skip tab refactoring entirely. Instead:
1. **Standalone Dialog**: `SpotifyImportDialog` - does not modify `EntityPickerDialog`.
2. **Simple Integration**: Add "Import from Spotify" button to `EntityListWidget` (next to "Add Artist").
3. **Fast Shipping**: Fewer files, no refactoring of working code, faster iteration.

## UX Flow
1. User clicks "Import from Spotify" button (in artist field using `EntityListWidget`).
2. `SpotifyImportDialog` opens with two panels:
   - **Left Panel**: Large editable `GlowPlainTextEdit` for pasting Spotify credit blocks.
   - **Right Panel**: Live parsed preview list with inline editing.
     - Rows: Name (editable), Roles (editable chip display), Delete button.
     - Unknown roles visually flagged (amber glow).
3. Controls at bottom:
   - `Parse` button (or auto-parse as user types).
   - `Import Selected` button - executes bulk creation/linking via `ContributorService`.
   - `Cancel` button.
4. On `Import Selected`:
   - For each parsed artist: `ContributorService.get_or_create(name, type='person')`.
   - For each role in artist's roles: `ContributorService.add_song_role(song_id, contributor_id, role_name)`.
   - Dialog closes; `EntityListWidget` refreshes via adapter, displaying new artists.
5. Result: New artists appear in the song's artist list with all roles assigned.

## Parsing Strategy (New Spotify Format)

**Input Structure**: Section-based (e.g., "Performers", "Writing & Arrangement", "Production & Engineering", "Sources").

**Parsing Steps**:
1. **Split by section headers** - Detect lines ending with or followed by empty line, then content. Common sections: "Performers", "Writing & Arrangement", "Production & Engineering", "Sources", "Management", etc.
2. **For each section** (except "Sources"):
   - Parse name + role(s) pairs:
     - `Name\nRole1 • Role2` → name="Name", roles=["Role1", "Role2"]
     - `Name\nRole` → name="Name", roles=["Role"]
     - Multiple lines per artist (one name, multiple role lines) → consolidate roles.
   - Normalize each role token.
3. **Skip "Sources" section** → Publisher linking deferred (TBD: not critical for MVP).
4. **Priority**: Parse "Writing & Arrangement" section (most important for app).
5. **Preserve original text** for audit.

## Role Normalization & Mapping
- **Source of Truth**: Hardcoded `ROLE_SYNONYMS` dict in parser (seeded from common Spotify roles).
- **Synonyms**: Map common aliases (e.g., `composer` -> `Composer`, `mixing` -> `Mix Engineer`, `feat.` -> skip).
- Matching is case-insensitive; punctuation is stripped.
- Unknown tokens are preserved as-is (original casing) and flagged in the preview UI with amber glow.
- **UI Validation**: When user selects a role in preview, check if it exists in DB `Roles` table. If not, display warning but allow import (user may correct in roles field).

## Example

Input (new Spotify format):
```
Performers
Kingsley Okorie
Bass

Benjamin James
Drums

Writing & Arrangement
Kingsley Chukwudi Okorie
Composer • Lyricist

Benjamin Chukwudi James
Composer • Lyricist

Jennifer Ejoke
Composer • Lyricist

Production & Engineering
Kingsley Okorie
Producer • Recording Engineer

Benjamin James
Producer • Recording Engineer

Spax
Mixing Engineer

Gerhard Westphalen
Mastering Engineer

Sources
Sounds From The Cave/RCA Records
```

Parsed output (JSON per item):
```json
[
  {
    "name": "Kingsley Chukwudi Okorie",
    "roles": ["Composer", "Lyricist"],
    "section": "Writing & Arrangement",
    "source": "spotify_import"
  },
  {
    "name": "Benjamin Chukwudi James",
    "roles": ["Composer", "Lyricist"],
    "section": "Writing & Arrangement",
    "source": "spotify_import"
  },
  {
    "name": "Jennifer Ejoke",
    "roles": ["Composer", "Lyricist"],
    "section": "Writing & Arrangement",
    "source": "spotify_import"
  }
]
```

(Publisher extraction deferred—not critical for MVP)

## Reference Parser (Python)
```python
# src/utils/spotify_credits_parser.py
import re

ROLE_SEPARATORS = re.compile(r'\s*[•·,/;&]\s*|\s+and\s+|\s*&\s*', flags=re.IGNORECASE)
SECTION_HEADER = re.compile(r'^(Performers|Writing\s*&\s*Arrangement|Production\s*&\s*Engineering|Sources|Management|Personnel)', re.IGNORECASE)

# Seeded from DB Roles table + common synonyms
ROLE_SYNONYMS = {
    'composer': 'Composer',
    'lyricist': 'Lyricist',
    'producer': 'Producer',
    'mixing': 'Mixing Engineer',
    'mix engineer': 'Mixing Engineer',
    'recording engineer': 'Recording Engineer',
    'mastering engineer': 'Mastering Engineer',
    'vocals': 'Vocals',
    'bass': 'Bass',
    'drums': 'Drums',
}

def normalize_role(token: str) -> str:
    """Clean punctuation, normalize to canonical role."""
    t = re.sub(r'[().]', '', token).strip().lower()
    return ROLE_SYNONYMS.get(t, token.strip().title())

def parse_spotify_credits(text: str, include_sections=None):
    """
    Parse Spotify credits by section.

    Args:
        text: Raw Spotify credits block text.
        include_sections: List of sections to parse (default: ["Writing & Arrangement"]).
                         Other valid: "Performers", "Production & Engineering", etc.

    Returns:
        List of dicts: [{"name": str, "roles": list, "section": str, "source": str}]
    """
    if include_sections is None:
        include_sections = ["Writing & Arrangement"]

    text = text.replace('\r\n', '\n').strip()

    # Split by section headers
    sections = {}
    current_section = None
    current_content = []

    for line in text.split('\n'):
        match = SECTION_HEADER.match(line)
        if match:
            # Save previous section
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            # Start new section
            current_section = line.strip()
            current_content = []
        elif current_section:
            current_content.append(line)

    # Save last section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content).strip()

    # Parse artists from included sections
    artists = []
    for section_name, content in sections.items():
        # Normalize section name for matching
        section_lower = section_name.lower()
        if not any(s.lower() in section_lower for s in include_sections):
            continue

        # Parse artist/role pairs in this section
        artists.extend(_parse_section(content, section_name))

    return artists

def _parse_section(content: str, section_name: str) -> list:
    """Parse artist/role pairs within a section."""
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    artists = []

    i = 0
    while i < len(lines):
        name = lines[i]
        roles = []

        # Collect all role lines following the name
        i += 1
        while i < len(lines) and not _is_artist_name(lines[i]):
            role_line = lines[i]
            tokens = ROLE_SEPARATORS.split(role_line)
            roles.extend([normalize_role(t) for t in tokens if t.strip()])
            i += 1

        if name and roles:
            artists.append({
                "name": name,
                "roles": roles,
                "section": section_name,
                "source": "spotify_import"
            })

    return artists

def _is_artist_name(line: str) -> bool:
    """Heuristic: A line is an artist name if it doesn't look like a role."""
    # Roles typically have multiple words or are in ROLE_SYNONYMS
    tokens = line.split()
    if len(tokens) > 3:  # Artist names are usually 2-3 words
        return False
    # Check if it looks like a known role
    lower = line.lower()
    if any(role.lower() in lower for role in ROLE_SYNONYMS.values()):
        return False
    return True

```

## Data Model

**Parser Output**:
```python
[
    {
        "name": str,           # Artist name
        "roles": list[str],    # Canonical roles (or original if unmapped)
        "section": str,        # e.g., "Writing & Arrangement", "Performers"
        "source": "spotify_import"
    }
]
```

**UI Preview State** (in dialog):
- Same as above + UI-specific tracking (e.g., `is_selected: bool`, `unknown_roles: list[str]`)

## Edge Cases to Handle

- **Blocks with only a name (no role)** - Skip (need at least name + 1 role to import).
- **Parenthetical roles**: `John Doe (Lyricist)` - Strip parentheses when parsing.
- **Multiple role separators**: `Composer • Producer / Lyricist` - Split correctly on all separators.
- **Duplicate names in same section** - Include both (user may have different roles).
- **Non-ASCII names** - Preserve original characters exactly.
- **Section headers with variations**: "Writing & Arrangement", "Writing and Arrangement", etc. - Normalize matching.
- **Multi-line role lists**:
  ```
  Kingsley Okorie
  Producer
  Recording Engineer
  ```
  → Collect both roles.
- **Unknown roles** - Preserve as-is and flag in UI.

## Tests (Required)
- `tests/unit/utils/test_spotify_credits_parser.py`
  - **Test 1**: Full Spotify example (Performers, Writing & Arrangement, Production, Sources) → Extract Writing & Arrangement artists only.
  - **Test 2**: Writing & Arrangement section → Correctly parse all 3 artists + roles.
  - **Test 3**: Multi-line roles (artist name, then multiple role lines) → Consolidate all roles.
  - **Test 4**: Multiple role separators (`Composer • Producer / Lyricist`) → All 3 roles extracted.
  - **Test 5**: Unknown role tokens → Preserved with original casing.
  - **Test 6**: Non-ASCII names (`José`, `Müller`, etc.) → Preserved exactly.
  - **Test 7**: Parenthetical roles (`John (Lyricist)`) → Parentheses stripped.
  - **Test 8**: Empty/whitespace-only input → Returns empty artists list.
  - **Test 9**: Only names, no roles in section → Skip (no artists returned).
  - **Test 10**: Duplicate names, different roles → Both included.
  - **Test 11**: Section name variations ("Writing & Arrangement" vs "Writing and Arrangement") → Both matched.

## UI Implementation Notes

### SpotifyImportDialog (new file: `src/presentation/dialogs/spotify_import_dialog.py`)
**Layout**: Two-panel horizontal split, buttons at bottom.

**Left Panel** (textarea):
- `GlowPlainTextEdit` for pasting Spotify credits (no character limit, scrollable).
- Connected to `textChanged` signal → triggers auto-parse.
- Placeholder: "Paste Spotify credits here (one artist per block)..."

**Right Panel** (preview list):
- Custom `QWidget` or `QListWidget` showing parsed artists.
- Each row is a `SpotifyArtistItemWidget`:
  - **Name**: Editable `GlowLineEdit` (user can fix typos).
  - **Roles**: Editable `ChipTrayWidget` (shows parsed roles as chips).
    - On chip click → open dropdown menu with canonical roles from DB (for easy remapping).
    - On chip creation → auto-validate against DB; if not found, flag with amber glow.
  - **Delete button**: Remove this artist from preview.
  - **Visual flag**: If any role is unknown (not in DB), show amber glow on that row's background.

**Status area** (below textarea):
- Show parse status: "Parsing..." / "3 artists parsed" / "Error: invalid input" etc.
- Count unknown roles: "⚠️ 2 unknown roles detected" (clickable to highlight them).

**Controls** (bottom):
- `Parse` button (manual re-parse if needed; auto-parse is default).
- `Import Selected` button (enabled only if ≥1 artist parsed; primary action).
- `Cancel` button (closes dialog, discards changes).

### SpotifyArtistItemWidget (new file: `src/presentation/widgets/spotify_artist_item_widget.py`)
Custom widget for each artist row in preview:
- Horizontal layout: Name | Roles | Delete
- Name field: `GlowLineEdit`, value = artist name (editable).
- Roles field: `ChipTrayWidget` or custom role display.
- Delete button: `GlowButton` with icon (✕ or 🗑).
- Background color: Normal gray, or amber if unknown roles detected.

## Integration Points

### 1. SpotifyImportDialog in Song Editor (Primary)
**Location**: Open from song editor when user wants to import credits.

**Scope**:
- Import artists with roles (from "Writing & Arrangement" section by default; configurable).
- Optionally import publisher (from "Sources" section).

**Integration Steps**:
1. User clicks "🎵 Import from Spotify" button (location TBD: in artist field, or in song form somewhere).
2. Dialog opens with: `service_provider`, `current_song_id`, `parent`.
3. User pastes Spotify credits → Auto-parse → Preview.
4. Dialog shows parsed artists + roles, editable, with import button.
5. On "Import": For each artist, call `ContributorService.get_or_create()` + `add_song_role()` for each role.
6. Dialog closes; song editor refreshes to show new data.

### 2. EntityListWidget Integration (Conditional)
**Current Plan**: Add button to `EntityListWidget` IF only editing song artists in isolation.

**Concern Raised**: `EntityListWidget` is reused across app (artists, aliases, members, publishers, etc.), so a Spotify button would appear in many places where it's not appropriate.

**REVISED APPROACH**:
- **Do NOT add button to `EntityListWidget`** unconditionally.
- Instead, **add button directly to song editor form** (e.g., in the artist input area or as a separate "Advanced" section).
- This keeps Spotify import contextual to songs and prevents confusion elsewhere.

### 3. Service Layer Integration
- **ContributorService.get_or_create(name, type='person')** - Reuse existing, no changes.
- **ContributorService.add_song_role(song_id, contributor_id, role_name)** - Reuse existing, no changes.
- **Role validation**: In dialog, query DB `Roles` table before calling `add_song_role()`. If role not found, warn user but allow manual entry in preview.

### 4. No New Controller Needed
- Orchestration lives in `SpotifyImportDialog._on_import_selected()`.
- Parser is pure utility in `src/utils/spotify_credits_parser.py`.

## Acceptance Criteria
- ✅ Parser correctly turns the example input into 3 parsed artist entries with correct roles.
- ✅ Dialog shows parsed preview, allows inline name/role edits, delete entries.
- ✅ Unknown roles are preserved and visually flagged (amber glow).
- ✅ Import button calls `get_or_create()` + `add_song_role()` for each artist+role.
- ✅ After import, dialog closes and `EntityListWidget` refreshes to show new artists.
- ✅ All 10 parser tests pass; no crashes on edge cases.

## Implementation Plan (Optimized - 5 commits, 2 days)

### Commit 1: Parser + Unit Tests
**Files**:
- `src/utils/spotify_credits_parser.py` (pure parser function + role normalization).
- `tests/unit/utils/test_spotify_credits_parser.py` (10 test cases).

**Scope**:
- Implement `parse_spotify_credits(text: str) -> list[dict]` - returns artists from "Writing & Arrangement" section.
- Hardcoded `ROLE_SYNONYMS` dict with common mappings.
- `normalize_role(token: str) -> str` - clean punctuation, lowercase, lookup in synonyms or title-case.
- Section detection, name/role heuristics, multi-line role consolidation.

**Estimate**: 2 hours.

---

### Commit 2: SpotifyArtistItemWidget (UI Component)
**Files**:
- `src/presentation/widgets/spotify_artist_item_widget.py` (custom widget for one artist row).

**Scope**:
- `SpotifyArtistItemWidget(QWidget)`:
  - Constructor: name (str), roles (list[str]), service_provider.
  - Layout: Name `GlowLineEdit` | Roles `ChipTrayWidget` | Delete button.
  - Getters: `get_name()`, `get_roles()`.
  - Setter: `set_roles(list)`, `mark_unknown_roles()` (amber glow).
  - Signal: `delete_requested` emitted on delete button click.
  - Role chips: On click, open dropdown with canonical roles from DB for quick selection.

**Estimate**: 1.5 hours.

---

### Commit 3: SpotifyImportDialog (Main Dialog)
**Files**:
- `src/presentation/dialogs/spotify_import_dialog.py` (main dialog).

**Scope**:
- `SpotifyImportDialog(QDialog)`:
  - Constructor: `service_provider`, `context_adapter` (current song context), `parent`.
  - Init UI: Left textarea + Right preview list + bottom controls.
  - Auto-parse on textarea text change.
  - Preview update: For each parsed artist, create `SpotifyArtistItemWidget`, check roles against DB.
  - Highlight unknown roles: Query DB `Roles` table, mark mismatches with amber.
  - Delete handler: Remove row from preview.
  - Name/role edit handlers: Update in-memory list.
  - Import logic: Loop through all visible rows → `get_or_create()` + `add_song_role()`.
  - Close dialog on success, emit signal with list of imported artists (for logging).

**Estimate**: 3 hours.

---

### Commit 4: Integration (Location TBD)
**Files**:
- `src/presentation/dialogs/spotify_import_dialog.py` (finalize).
- Location for button: TBD based on where Spotify import should appear (likely song editor form, not EntityListWidget).

**Scope**:
- Decide where the "🎵 Import from Spotify" button lives:
  - **Option A**: Direct button in song form (best - contextual to songs).
  - **Option B**: In a "Tools" menu or advanced options panel.
  - **Option C**: Accessible only from Artist tab of song editor.
- Hook up button to open `SpotifyImportDialog`.
- On dialog accept: Refresh song data (artists + publisher if applicable).

**Estimate**: 1.5 hours (includes TBD research).

---

### Commit 5: QA + Documentation
**Files**:
- Update `docs/spotify_import.md` (this file, already done).
- Add usage example in widget docstring.

**Scope**:
- Manual testing: Paste Spotify credits, verify parse, edit names/roles, import.
- Edge cases: Unknown roles, non-ASCII names, malformed input, empty input.
- Integration test: Verify artists appear in song editor after import.

**Estimate**: 1 hour + manual testing.

---

## Summary

### Scope
- **Parse Spotify credits** by section (focus on "Writing & Arrangement").
- **Import artists + roles** to current song via `ContributorService`.
- **No modification** to `EntityListWidget` (avoid multi-place button confusion).
- **Contextual integration** - button placement TBD (likely song form, not generic widget).
- **Publisher extraction** - Deferred (not critical for MVP).

### Deliverables
- **Total files created**: 3 (`spotify_credits_parser.py`, `spotify_artist_item_widget.py`, `spotify_import_dialog.py`).
- **Total files modified**: 0 (no refactoring of existing code; button location TBD).
- **Lines of code**: ~650 total (parser 120, parser tests 180, widget 120, dialog 200, integration TBD).
- **No refactoring** of existing dialogs or large-scale changes.
- **Shipping timeline**: 2-3 days, 5 commits, zero risk to existing features.

### Next Steps
1. Review plan with user.
2. Implement Commit 1 (parser + tests).
3. Implement Commit 2 (widget).
4. Implement Commit 3 (dialog).
5. Research + implement Commit 4 (find best button location in song form).
6. QA + Commit 5.
