---
tags:
  - search
  - feature
  - status/planned
  - priority/medium
links:
  - "[[GitHub #10]]"
---

# T-16: Advanced Search Syntax

## Goal
Implement robust search syntax (e.g., `artist:Beatles year:1960..1970`) to replace simple string matching.

## Requirements
*   **Field Targeting**: `field:value` (e.g., `genre:Rock`)
*   **Logical Operators**: `AND`, `OR`, `NOT` (plus symbols `&`, `|`)
*   **Range Queries**: `bpm:120..130`, `year:>2000`
*   **Exact Match**: `"Exact Phrase"`

## Notes
See GitHub Issue #10 for original discussion.
