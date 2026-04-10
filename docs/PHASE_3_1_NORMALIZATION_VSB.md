# PHASE 3.1: NORMALIZATION & SEARCH FOUNDATION

## 1. Feature Chain & Objective

**Objective:** Unify normalization to a single source of truth (`src/utils/text.py`) and apply diacritic-agnostic search across the architectural stack without generating relationship "noise".

**Chain:** `FilingService` (File Writer) & Services (Search Index) -> `utils/text.py` -> `rules.json` (Custom Transliterations)

## 2. Execution Steps

### Step 1: Configuration Extraction

- Move the hardcoded Slavic mapping block out of `FilingService`.
- Inject a `"transliterations"` dictionary map into `rules.json`.

### Step 1b: JSON Loader Utility (`src/utils/json_loaders.py`)

- Create two dedicated loader functions (no other file should import `json` for these):
  - `load_rules() -> dict` — loads `json/rules.json`
  - `load_id3_frames() -> ID3FrameMapping` — migrated from `src/services/metadata_frames_reader.py`
- `FilingService`, `text.py`, and `MetadataParser` all call these loaders instead of loading JSON directly.

### Step 2: The Core Utility (`src/utils/text.py`)

Implement the unified string handlers:

1. `strip_diacritics(text: str, trans_map: dict) -> str`
   - Applies the custom `rules.json` map (e.g. `Đ -> Dj`).
   - Applies `unicodedata.normalize("NFKD")` to strip complex accents (`Noëp -> Noep`).
   - Retains original casing (Used by File Writer).
2. `normalize_for_search(text: str, trans_map: dict) -> str`
   - Calls `strip_diacritics(text, trans_map).lower()`.
   - Used exclusively to populate database `_Search` columns.

### Step 3: FilingService Consolidation

- Refactor `src/services/filing_service.py` to strip out `_sanitize_for_filesystem`'s duplicate unicode logic.
- Pipe filesystem generation through the new `utils/text.py::strip_diacritics`.

### Step 4: The Database Migration

- Add `_Search` string columns via `ALTER TABLE`:
  - `ArtistNames.DisplayName_Search`
  - `Songs.MediaName_Search`
  - `Albums.Title_Search`
  - `Publishers.Name_Search`
  - `Tags.Name_Search`
- Generate a fast Python script to back-fill existing rows using `normalize_for_search`.

### Step 5: Service Layer Hooks

- **Write Hooks:** Instrument `IdentityService` and `CatalogService` `save`/`update` methods to populate the `_Search` columns before hitting the repositories.
- **Read Hooks (The Fix):** Instrument the `search_` methods in the services to run the incoming `/search?query=Noëp` through `normalize_for_search()` so that the SQL query matches the shadow column's stripped format.
- **Search Column Rule:** `DisplayName_Search` stores only the entity's own normalized display name. Alias and group membership joins are resolved at query time, only when Deep Search is enabled in the UI.

## 3. Outcome Matrix (VSB)

| Context            | Input           | Condition               | Expected Result                                                                               |
| :----------------- | :-------------- | :---------------------- | :-------------------------------------------------------------------------------------------- |
| **JSON Extension** | `ß` typed in UI | Mapped to `ss` in rules | String resolves to `ss` natively.                                                             |
| **Target Path**    | `MÖTLEY CRÜE`   | Saving File             | Folder becomes `/MOTLEY CRUE/` (Case preserved).                                              |
| **Shadow Writes**  | New Identity    | Service Save            | `Noëp` is saved as `"noep"` inside `DisplayName_Search`.                                      |
| **Search Hit**     | `noep` typed    | Deep Search OFF         | Fast SQL `LIKE` hit against `DisplayName_Search`. Returns `Noëp`. No songs polluted.          |
| **Search Hit**     | `spice` typed   | Deep Search ON          | Query joins alias and group membership tables at runtime. Returns artists related to "spice". |
