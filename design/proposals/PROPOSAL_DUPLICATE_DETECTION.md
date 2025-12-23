---
tags:
  - layer/core
  - domain/import
  - status/draft
  - size/medium
links:
  - design/reference/LEGACY_LOGIC.md
  - design/DATABASE.md
---

# Architectural Proposal: Duplicate Detection & Import Logic

**Objective**: Prevent the user from adding the same song multiple times, or accidentally importing a file that already exists in the library under a different path.

**Context**: 
Legacy Gosling 1 had no database; dupe detection was visual. Gosling 2 must be stricter.

---

## 1. The Detection Tier (The 3-Step Check)

When a file is dragged onto the app (or scanned), we run this check **BEFORE** creating a `Song` entity.

### Tier 1: ISRC Match (Definitive)
*   **Input**: Read `TSRC` frame from ID3.
*   **Query**: `SELECT * FROM Songs JOIN MediaSources ON Songs.SourceId = MediaSources.Id WHERE Songs.ISRC = ?`
*   **Verdict**: If match found, it IS the same recording.
    *   *Action*: Prompt User: "This ISRC already exists in library (Title: X). Link this file as a new Source?"

### Tier 2: File Hash Match (Bit-Perfect)
*   **Input**: Calculate MD5 (or SHA-1) of the file content.
    *   *Optimization*: Hash first 64KB + last 64KB + file size to avoid reading 100MB files.
*   **Query**: `SELECT * FROM MediaSources WHERE FileHash = ?`
*   **Verdict**: If match found, the file is bit-for-bit identical to one we have.
    *   *Action*: Auto-Skip (Log it: "Skipped exact duplicate: filename.mp3").

### Tier 3: Metadata Composite (Fuzzy)
*   **Input**: `Artist`, `Title`, `Duration`.
*   **Query**: `SELECT * FROM Songs WHERE Title LIKE ? AND Duration BETWEEN ? AND ?`
*   **Logic**:
    *   Normalize strings (lowercase, strip non-alphanumeric).
    *   Duration tolerance: +/- 2 seconds.
*   **Verdict**: Probable duplicate.
    *   *Action*: Prompt User: "Possible duplicate found (Title: X). Import anyway?"

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

*   **MediaSources Table**: Add `FileHash` column (String, Indexed).
*   **Indexing**: Ensure `ISRC` and `Title` are indexed for speed.

---

## 4. Implementation Plan

- [ ] Add `FileHash` to `MediaSources` schema logic.
- [ ] Create `DuplicateScannerService`.
- [ ] Implement `calculate_quick_hash(filepath)` utility.
- [ ] Add "Import Report" UI dialog.

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
