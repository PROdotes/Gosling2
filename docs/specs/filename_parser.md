# Spec: FilenameParser

## Overview
As per the requirement in `temp/upcoming_features.md`, the FilenameParser is a dynamic utility that allows users to define custom string patterns for extracting metadata from file stems. 

## Target: `src/services/filename_parser.py`

### Responsibility
Stateless utility for compiling tokenized patterns (e.g., `{Artist} - {Title}`) into regular expressions and applying them to filenames.

---

## 1. VSB Outcome Matrix

**Contract**: `parse_with_pattern(filename: str, pattern: str) -> Dict[str, str]`

| Input (Filename Stem) | Pattern | Outcome | Rationale |
| :--- | :--- | :--- | :--- |
| `Oliver - Cezanj` | `{Artist} - {Title}` | `{"Artist": "Oliver", "Title": "Cezanj"}` | Standard separator. |
| `01 - Oliver - Cezanj` | `{Ignore} - {Artist} - {Title}` | `{"Artist": "Oliver", "Title": "Cezanj"}` | `{Ignore}` removes junk. |
| `Oliver (2024) - Cezanj` | `{Artist} ({Year}) - {Title}` | `{"Artist": "Oliver", "Year": "2024", "Title": "Cezanj"}` | Captures embedded attributes. |
| `Oliver_Cezanj_120` | `{Artist}_{Title}_{BPM}` | `{"Artist": "Oliver", "Title": "Cezanj", "BPM": "120"}` | Custom delimiters (`_`). |

---

## 2. Technical Strategy

### 2.1 Pattern Compilation
1.  **Token Discovery**: Identify tokens wrapped in curly braces: `{Artist}`, `{Title}`, `{Album}`, `{Year}`, `{BPM}`, `{Genre}`, `{Publisher}`, `{ISRC}`, `{Ignore}`.
2.  **Regex Generation**: Replace tokens with named capture groups:
    - `{Artist}` -> `(?P<Artist>.+?)`
    - `{Ignore}` -> `(?:.*?)` (Non-capturing or discarded)
    - Literal characters (dashes, spaces, underscores) are escaped for regex safety.
3.  **Boundary Anchors**: Patterns should be anchored to the start (`^`) and end (`$`) of the filename stem to ensure full string coverage.

### 2.2 Execution Flow
1.  **Pre-processing**: Strip the file extension from the filename.
2.  **Match**: Attempt `re.match` with the compiled regex.
3.  **Sanitization**: `strip()` all resulting values. Discard any `Ignore` groups.
4.  **Failure**: If no match, return an empty dictionary (Partial matches are invalid for finalized parsing).

---

## 3. Public API

### `parse_with_pattern(filename: str, pattern: str) -> Dict[str, str]`
The primary entry point. 

---

## 4. Testing Protocol
- Tests valid patterns against various delimiters.
- Tests that `{Ignore}` correctly discards data.
- Tests handling of malformed patterns (should not crash).
- Tests edge cases like filenames with multiple extensions or dots.

---

## 3. Public API (Proposed Signature)

### `parse_filename(filename: str) -> Dict[str, Any]`
The entry point. Performs extension stripping and runs the heuristic chain.

---

## 4. Testing Protocol
- Follows `docs/testing/TDD_STANDARD.md`.
- No DB required (Stateless).
- Test cases for all permutations in the VSB Matrix.
