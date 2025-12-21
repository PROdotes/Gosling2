---
tags:
  - layer/ui
  - domain/table
  - status/on-hold
  - type/task
  - size/medium
links:
  - "[[PROPOSAL_METADATA_EDITOR]]"
---
# Inline Edit

**Task ID:** T-03  
**Layer:** UI  
**Score:** 8  
**Status:** ⏸️ On Hold (Permanent)

---

## Summary

Double-click cell editing in the library table view.

## Requirements

- Double-click any cell to edit inline
- Validation on blur
- Auto-save or staged commit
- Support for different editors (text, dropdown, chips)

## On Hold Reason (2025-12-21)

The Metadata Viewer Dialog is now a **read-only comparison view** for File vs Database metadata. 
Inline editing is deferred indefinitely. If editing is needed in the future, a separate dedicated 
editor UI will be designed rather than making the comparison view editable.

## Links

- [PROPOSAL_METADATA_EDITOR.md](../PROPOSAL_METADATA_EDITOR.md)
