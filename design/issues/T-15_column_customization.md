# Column Customization

**Task ID:** T-15  
**Layer:** UI  
**Score:** 8  
**Status:** 📋 Queued

---

## Summary

Let users reorder columns, show/hide columns, and save layouts as presets.

## Requirements

- Drag columns to reorder
- Right-click header to show/hide columns
- Save column order + visibility to SettingsManager
- (Optional) Loadouts: Multiple saved configurations

## Implementation

- `QHeaderView.setSectionsMovable(True)`
- `QHeaderView.sectionMoved` signal → save to settings
- Context menu on header for visibility toggle

## Links

- [PROPOSAL_LIBRARY_VIEWS.md](../PROPOSAL_LIBRARY_VIEWS.md) — Phase 3
