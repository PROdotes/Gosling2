---
tags:
  - layer/core
  - domain/import
  - status/active
  - size/medium
  - milestone/0.1.0
links:
  - design/reference/LEGACY_LOGIC.md
  - design/DATABASE.md
---

# Architectural Proposal: Duplicate Detection & Import Logic

**Objective**: Prevent the user from adding the same song multiple times, or accidentally importing a file that already exists in the library under a different path.

**Context**: 
- Legacy Gosling 1 had no database; dupe detection was visual.
- Current Gosling 2 uses filename-based detection (`genre\year\artist - title.mp3`), which **fails** when:
  - Same song is re-classified to a different genre (different folder path)
  - Same song is emailed multiple times with different filenames
- **Real-world use case**: Radio station receives same song 5 times in 2 weeks via email. Genre classification may change over time ("Hard Metal" → "Hard Rock").

---

## 1. The Detection Tier (The 2-Step Check for 0.1.0)

When a file is dragged onto the app (or scanned), we run this check **BEFORE** creating a `Song` entity.

### Tier 1: ISRC Match (Definitive) - **0.1.0**
*   **Input**: Read `TSRC` frame from ID3.
*   **Sanitization**: Normalize ISRC format by stripping dashes/spaces (e.g., `US-AB1-23-45678` → `USAB12345678`) before comparison.
*   **Query**: `SELECT * FROM Songs WHERE ISRC = ?` (using sanitized ISRC)
*   **Verdict**: If match found, it IS the same recording (ISRC is globally unique).
*   **Action**: Auto-skip with log: `"Duplicate ISRC detected: [ISRC] - [Title]"`
*   **UI Integration**: Existing duplicate detection already turns save button red on field edit - leverage this for ISRC field.
*   **Note**: Not all songs have ISRC (especially email submissions), so this is a first-pass filter.

### Tier 2: Audio-Only Hash Match (Bit-Perfect) - **0.1.0**
*   **Input**: Calculate hash of **MP3 audio frames only** (exclude ID3 tags).
*   **Why Audio-Only**: 
    - Same song may have different ID3v2 (start) or ID3v1 (end) tags.
    - Hashing entire file would fail to detect duplicates with different metadata.
*   **Implementation**:
    - Use Mutagen to locate audio frame boundaries (skip ID3v2 header, skip ID3v1 footer).
    - Hash only the MPEG audio data.
    - Store in `MediaSources.AudioHash` (new column).
*   **Query**: `SELECT * FROM MediaSources WHERE AudioHash = ?`
*   **Verdict**: If match found, the audio is bit-for-bit identical.
*   **Action**: Auto-skip with log: `"Duplicate audio detected: [filename]"`

### Tier 3: Metadata Composite (Fuzzy) - **DEFERRED to 0.2.0**
*   **Input**: `Artist`, `Title`, `Duration`.
*   **Query**: `SELECT * FROM Songs WHERE Title LIKE ? AND Duration BETWEEN ? AND ?`
*   **Logic**:
    *   Normalize strings (lowercase, strip non-alphanumeric).
    *   Duration tolerance: +/- 2 seconds.
*   **Verdict**: Probable duplicate.
*   **Action**: Prompt User: "Possible duplicate found (Title: X). Import anyway?"
*   **Why Deferred**: Least reliable, requires UI prompts and decision-making logic.

---

## 2. The Import Workflow (UI)

When dropping 100 files:

1.  **Scanning Phase**: Parse ID3 tags into memory. Show progress bar.
2.  **Deduplication Phase**: Run the 3-Tier check against DB.
3.  **The "Conflict Resolution" Dialog**:
    *   Show list of **New** vs **Duplicates**.
    *   Options:
        *   "Skip Duplicates" (Default)
        *   "Import All (Allow Duplicates)"
        *   "Link as Alias" (Advanced - requires Multi-Source support)

---

## 3. Database Updates

*   **MediaSources Table**: Add `AudioHash` column (String, Indexed) to store hash of MP3 audio frames only.
*   **Songs Table**: Ensure `ISRC` column is indexed for fast lookups.
*   **Note**: `AudioHash` is stored in `MediaSources` (not `Songs`) because the same song may have multiple sources with different audio quality/encoding.

---

---

## 4. Implementation Plan (0.1.0 Scope)

### Phase 0: ISRC Field Validation (Prerequisite)
**Goal**: Centralize ISRC validation to prevent code duplication across UI, service layer, and duplicate detection.

**Current Problem**: 
- `metadata_service.py` has hardcoded ISRC regex (line 239)
- No real-time UI feedback
- No sanitization (just validation + null on failure)

**Solution**: Single Source of Truth in Yellberus + shared utilities.

#### Step 1: Centralize Pattern in Yellberus
- [x] Add `validation_pattern: Optional[str]` attribute to `FieldDef` class.
- [x] Update `isrc` field definition in `FIELDS`:
  ```python
  FieldDef(
      name='isrc',
      ui_header='ISRC',
      db_column='S.ISRC',
      id3_tag='TSRC',
      validation_pattern=r'^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$',  # Sanitized format (no dashes)
      searchable=False,
  )
  ```

#### Step 2: Create Shared Utilities
- [x] Create `src/utils/validation.py` (or add to existing utils module):
  ```python
  def sanitize_isrc(isrc: str) -> str:
      """Strip dashes, spaces, convert to uppercase."""
      if not isrc:
          return ""
      return re.sub(r'[-\s]', '', isrc).upper()
  
  def validate_isrc(isrc: str) -> bool:
      """Validate ISRC against Yellberus pattern."""
      from src.core.yellberus import get_field
      field = get_field('isrc')
      if not field or not field.validation_pattern:
          return True  # No pattern defined, pass
      sanitized = sanitize_isrc(isrc)
      return bool(re.match(field.validation_pattern, sanitized))
  ```

#### Step 3: Refactor Existing Code (Eliminate Duplication)
- [x] **`metadata_service.py` (lines 236-242)**:
  - **Remove** hardcoded `isrc_pattern = r'^[A-Z]{2}-?[A-Z0-9]{3}-?\d{2}-?\d{5}$'`
  - **Replace** with:
    ```python
    from src.utils.validation import validate_isrc, sanitize_isrc
    
    if song.isrc:
        if validate_isrc(song.isrc):
            song.isrc = sanitize_isrc(song.isrc)  # Store sanitized version
        else:
            logger.dev_warning(f"Invalid ISRC format: {song.isrc}, skipping ID3 write")
            # Keep DB value, just don't write to ID3
    ```

#### Step 4: Implement Real-Time UI Validation
- [x] **Side Panel** (`src/presentation/side_panel.py`):
  - On ISRC field edit, call `validate_isrc()`
  - Change text color: red = invalid, normal = valid
  - Leverage existing validation infrastructure (similar to required field highlighting)
  - **CRITICAL**: App uses dark theme (white text). Do NOT hardcode `QColor(0,0,0)` for valid text - restore original palette instead!

#### Step 5: Use in Duplicate Detection
- [x] **Duplicate Scanner** (`src/services/duplicate_scanner.py`):
  - Use `sanitize_isrc()` before DB comparison
  - Ensures `US-AB1-23-45678` matches `USAB12345678`

**Rationale**: 
- **No duplication**: All ISRC logic flows through Yellberus + utils
- **Single source of truth**: Change the regex once in Yellberus, everywhere updates
- **Consistent behavior**: UI, service layer, and duplicate detection all use same validation

### Phase 1: Database Schema
- [x] Add `AudioHash` column to `MediaSources` table (String, Indexed).
- [x] Ensure `ISRC` column in `Songs` table is indexed.

### Phase 2: Core Logic
- [x] Create `DuplicateScannerService` in `src/services/`.
- [x] Implement `calculate_audio_hash(filepath)` utility:
  - Use Mutagen to parse MP3 structure.
  - Skip ID3v2 header (first N bytes, size in header).
  - Skip ID3v1 footer (last 128 bytes if present).
  - Hash only the MPEG audio frames.
- [x] Implement `sanitize_isrc(isrc)` utility → Strip dashes, spaces, convert to uppercase.
- [x] Implement `check_isrc_duplicate(isrc)` → Sanitize input, query `Songs` table.
- [x] Implement `check_audio_duplicate(audio_hash)` → Query `MediaSources` table.

### Phase 3: Integration
- [x] Update import workflow in `library_widget.py`:
  - Before creating `Song`, run ISRC check (sanitized).
  - Before creating `MediaSource`, calculate and check audio hash.
  - Auto-skip duplicates with log message (no UI prompt for 0.1.0).
- [x] Integrate with existing duplicate detection UI:
  - ISRC field edit should trigger duplicate check.
  - Red save button should appear if ISRC collision detected.
- [x] Add logging for skipped duplicates (user-facing and dev logs).

### Phase 4: Testing
**Per TESTING.md**: Tests separated by Intent (Logic vs Robustness), mirrored to `src/` structure, minimum 80% coverage.

#### Phase 4a: ISRC Validation Tests

**Logic Tests** (`tests/unit/core/test_yellberus.py` - add to existing):
- [x] Valid ISRC formats: `US-AB1-23-45678`, `USAB12345678`, `USAB12345678` (no dashes)
- [x] Invalid ISRC formats: too short, wrong country code, non-alphanumeric characters
- [x] `sanitize_isrc()` utility: strips dashes, spaces, converts to uppercase
- [x] Yellberus field definition has `validation_pattern` attribute populated

**Robustness Tests** (`tests/unit/core/test_yellberus_mutation.py` - create if doesn't exist):
- [x] Null bytes in ISRC field
- [x] 100,000-character ISRC string (exhaustion)
- [x] SQL injection attempts in ISRC field (e.g., `'; DROP TABLE Songs--`)
- [x] Unicode/emoji in ISRC field

**UI Tests** (`tests/unit/presentation/test_side_panel.py` - add to existing):
- [x] Text color changes to red on invalid ISRC input (real-time validation)
- [x] Red save button appears when ISRC matches existing song (duplicate detection)

#### Phase 4b: Duplicate Detection Tests

**Logic Tests** (`tests/unit/services/test_duplicate_scanner.py` - new file):
- [x] `calculate_audio_hash()` with clean MP3 (ID3v2 header + audio frames + ID3v1 footer)
- [x] Same audio with different ID3 tags → Same hash
- [x] Different audio files → Different hashes
- [x] `check_isrc_duplicate()` with sanitized ISRC → Finds existing song
- [x] `check_audio_duplicate()` with hash → Finds existing MediaSource
- [x] No duplicate found → Returns None

**Robustness Tests** (`tests/unit/utils/test_audio_hash_mutation.py` - new file):
**Rationale**: Trust boundary (external files) per TESTING.md Law 7.
- [x] Corrupt MP3: Missing ID3v2 header → Graceful failure (log error, skip hash)
- [x] Zero-byte file → Graceful failure
- [x] Huge MP3 (100MB+) → Hash completes without memory issues
- [x] File with only ID3 tags, no audio frames → Graceful failure
- [x] File path with null bytes → Graceful failure
- [x] Permission denied on file read → Graceful failure

**Integration Tests** (`tests/integration/test_import_workflow.py` - add to existing):
- [x] Import same file twice → Second import auto-skipped, logged
- [x] Import same audio with different metadata → Detected as duplicate via hash
- [x] Import different files → Both imported successfully
- [x] Import file with matching ISRC → Auto-skipped, logged
- [x] Import file with invalid ISRC → Imported, ISRC validation warning logged

#### Coverage Requirements (TESTING.md Law 8):
- [x] `src/services/duplicate_scanner.py` → 80%+ coverage
- [x] `src/utils/isrc_utils.py` (or wherever `sanitize_isrc()` lives) → 80%+ coverage
- [x] Run `python tools/audit_test_coverage.py` to verify

---

## 5. Mock Scenarios

**Scenario A: Re-importing the library folder**
*   User drags `Z:\Songs` into app.
*   App sees hashes match existing files.
*   Result: "0 New Songs, 5000 Duplicates Skipped." (Fast)

**Scenario B: Upgrading quality**
*   User drags `Song - High Quality.mp3`.
*   Tier 1 (ISRC) matches existing `Song - Low Quality.mp3`.
*   Result: Prompt "Duplicate ISRC found. Replace existing file?"
