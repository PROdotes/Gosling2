# Settings Architecture (agreed 2026-06-18)

Supersedes the old `SETTINGS_SCHEMA` / `_validate` / `api_schema` / `effective_settings` approach in
`config_service.py`. That design had the source of truth inverted (config.py defaults + sparse JSON
override) and split each setting's declaration across two drifting sites. Throw it out; do not patch it.

## The model

**Two objects:**

- **`Settings`** — a pydantic `BaseModel` holding the mutable/editable settings.
  **`json/settings.json` is the source of truth.** Load = `Settings.model_validate_json(file)`;
  the model instance is the in-memory mirror. NOT a sparse override over config defaults —
  the JSON holds the real values.
- **`config`** (`src/engine/config.py`) — immutable **code facts only**: `DB_PATH`, `FFMPEG_PATH`,
  `ProcessingStatus`, `SCALAR_VALIDATION`, etc. Never user-editable, never in the settings surface.

**A setting = one typed field on `Settings`.** Default + type + bounds live on the field:

```python
class Settings(BaseModel):
    scrubber_auto_play: bool = True
    song_row_height: int = Field(20, ge=16, le=120)
    tag_delimiter: str = "::"
    credit_separators: list[str] = ["&", "feat.", "ft."]
    default_search_engine: SearchEngine = SearchEngine.google   # Enum -> select control
```

Adding a setting later = adding one field. It is then typed, readable everywhere via the live
`settings` instance, persisted, and appears in the editor automatically.

**Pydantic does the heavy lifting** (this is a FastAPI/pydantic stack):

- validation — `Field(ge=, le=)`, Enums, validate-on-assignment (replaces `_validate`)
- JSON I/O — `model_validate_json` / `model_dump_json` (replaces reader + overlay + `_default`)
- editor schema — `model_json_schema()`, served by FastAPI, drives the frontend form (replaces `api_schema`)

So `ConfigService` + `SETTINGS_SCHEMA` + `_validate` + `api_schema` + `effective_settings` +
`_default` largely evaporate into the model class.

**Types the value can't reveal on its own** (everything else is inferred from the field type):

- `select` — constrained str; an Enum declares the option set
- `path` — str wanting a folder-picker + existence check in the editor
- `list` — chip editor; semantics vary per field

The old "type-completeness gap" (collectPatch/buildControl/_validate/_set_live not handling
int/string) dissolves — replace that machinery, don't extend it.

**Read sites:** import the single live `settings` instance and read `settings.x` (analogous to
`config.X` today). Edit flow: validated assignment -> `model_dump_json` to `json/settings.json`
-> set live; editor renders from `model_json_schema()`.

## Scope

- **First pass (narrow, reviewable on its own):** stand up the `Settings` model, port the
  *already-wired* settings 1:1 (no new settings), invert the source of truth, swap those read
  sites over.
- **Deferred to a later pass:** relocating misfiled items out of `config.py`, and adding brand-new
  settings (tag delimiter, credit separators, default year, blockers, song row height).

## Files involved

- `src/services/config_service.py` — largely replaced by the `Settings` model
- `src/engine/routers/settings.py` — GET /api/v1/settings serves `model_json_schema()`
- `src/static/js/dashboard/components/settings_modal.js` — form renders from the JSON schema
- `src/engine/config.py` — keeps ONLY immutable code facts
- Tests: `tests/test_services/test_config_service.py`, `tests/test_api/test_settings_api.py`,
  `tests/js/unit/settings_modal.test.js`

Related: the settings/rules editor parity work (last two gaps vs the old PyQt exe; parity source is
the old exe's observed behavior, not git history). The prior mess came from compounding "finish
later" deferrals — finish each unit fully in one pass.
