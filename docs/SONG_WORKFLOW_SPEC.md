# Song Workflow & Processing Status Spec

## processing_status Field (TXXX:STATUS in ID3)

| Value | Meaning |
|-------|---------|
| `2` | Imported, not auto-checked |
| `1` | Auto-checked (MusicBrainz etc.) — MusicBrainz skipped for now, so ingestion sets directly to `1` |
| `0` | Human reviewed and approved |

## is_active Field (Airplay Flag)

- Can **only** be toggled when `processing_status == 0`
- `0` = not in airplay rotation
- `1` = eligible for airplay logic to pick up
- A song can be `processing_status=0` but `is_active=0` (e.g. ok to play manually 2-3x/year but not in automated rotation)

## Ingestion Guards

Songs that fail these checks should be **blocked at ingestion** (not added to library):
- `duration_s` must be > 0 — broken files sometimes arrive with null/zero duration

## "Ready for Review" Prompt

Triggers when user opens a song where `processing_status == 1` AND all required fields are filled.

Prompt: **"Mark as reviewed?"** → sets `processing_status` to `0`

### Required Fields (minimum to be reportable)
- Title (`media_name`)
- Year
- Duration > 0 (ingestion guard — should never be missing if guard is in place)
- At least 1 Performer credit
- At least 1 Composer credit
- At least 1 Genre tag
- At least 1 Publisher

### Optional Fields (nice to have, not blocking review)
- ISRC — not all songs arrive with one
- BPM — to be automated via detection one day

## Full Pipeline to Z:\Songs

1. **Ingest** → `processing_status=1`, `is_active=0`
2. **User edits** missing fields in editor (credits, tags, publishers, scalars)
3. All required fields filled + `processing_status=1` → **prompt to mark reviewed** → `processing_status=0`
4. `processing_status` flips to `0` → **rename rules apply automatically**
5. If `AUTO_MOVE_ON_APPROVE=true`: move file to `LIBRARY_ROOT` (prompt first if `PROMPT_BEFORE_MOVE=true`)
6. User optionally toggles `is_active=1` (only available when `processing_status=0`)

## Config Settings Needed (src/engine/config.py)

| Setting | Type | Description |
|---------|------|-------------|
| `AUTO_MOVE_ON_APPROVE` | bool | Move file to `LIBRARY_ROOT` when `processing_status` set to `0` |
| `PROMPT_BEFORE_MOVE` | bool | If auto-move enabled, prompt user before moving (vs silent move) |
| `RENAME_RULES_PATH` | path | Path to JSON file containing rename rules |

## Future: Settings Frontend
A settings UI will eventually be needed to expose these config values. Deferred — config.py + env vars are sufficient for now.

## State Machine Summary

```
Ingestion → processing_status=2 → (auto-check, skipped for now) → processing_status=1
                                                                         ↓
                                                          user fills required fields
                                                                         ↓
                                                          prompt "Mark as reviewed?"
                                                                         ↓
                                                              processing_status=0
                                                                         ↓
                                                          is_active toggle unlocked
```
