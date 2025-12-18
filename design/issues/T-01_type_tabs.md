---
tags:
  - layer/ui
  - domain/table
  - status/active
  - type/task
  - size/small
  - priority/high
links:
  - "[[PROPOSAL_LIBRARY_VIEWS]]"
  - "[[DATABASE]]"
---
# Type Tabs

**Task ID:** T-01  
**GitHub Issue:** #6  
**Layer:** UI  
**Score:** 15  
**Status:** 🟢 Next

---

## Summary

Filter library by content type using a horizontal tab bar above the library table.

---

## Tab Configuration

Types grouped for the tab bar:

| Tab Name | TypeIDs | DB Types |
|----------|---------|----------|
| All | — | (no filter) |
| Music | 1 | Song |
| Jingles | 2 | Jingle |
| Commercials | 3 | Commercial |
| Speech | 4, 5 | VoiceTrack, Recording |
| Streams | 6 | Stream |

**Note:** VoiceTrack and Recording are grouped as "Speech" since both are direct voice content.

---

## Requirements

### Functional
- Tab bar above library: `All | Music (234) | Jingles (12) | Commercials (45) | Speech (8) | Streams (2)`
- Clicking tab applies `WHERE TypeID IN (...)` filter
- Show item count on each tab
- Persist last-used tab in SettingsManager
- Default to last selection (or "All" on first launch)

### Visual
- Default Qt `QTabBar` for MVP
- **Future:** May need custom buttons when adding Sweepers/SFX types (see UX design phase)

### Behavior
- Remember last selection across app restarts
- "All" shows everything (no filter applied)
- Counts update when library changes

---

## Implementation

### Files to Modify
- `src/presentation/widgets/library_widget.py` — Add tab bar
- `src/business/services/settings_manager.py` — Store/load tab selection

### Approach
1. Add `QTabBar` above `QTableView` in `LibraryWidget`
2. On tab change signal → update `QSortFilterProxyModel.setFilterFixedString()` or custom filter
3. Query `Types` table on init to populate tabs dynamically (future-proof)
4. Save selection to settings: `library/type_filter`

### Filter Logic
```python
# In proxy model or filter method
def filter_by_type(type_id: int | None):
    if type_id is None:  # "All" tab
        self.proxy.setFilterFixedString("")
    else:
        self.proxy.setFilterByColumn(TYPE_ID_COLUMN, type_id)
```

---

## Checklist

- [ ] Add `QTabBar` widget to library layout (above table)
- [ ] Populate tabs from `Types` table or hardcode MVP
- [ ] Connect `currentChanged` signal to filter method
- [ ] Implement filter in proxy model
- [ ] Add `library/type_filter` to SettingsManager
- [ ] Load saved tab on startup
- [ ] Save tab on change
- [ ] Test: Switching tabs filters correctly
- [ ] Test: Tab persists across app restart

---

## Open Questions

1. **Item counts on tabs?** — ✅ Yes, show counts
2. **Hide empty tabs?** — If no Commercials exist, hide that tab?

---

## Mockup

![Type Tabs Mockup](../mockups/type_tabs_mockup.png)

**Top:** Default PyQt style (MVP)  
**Bottom:** Future modern styling

---

## Links

- [PROPOSAL_LIBRARY_VIEWS.md](../proposals/PROPOSAL_LIBRARY_VIEWS.md)
- [DATABASE.md](../../DATABASE.md) — Types table
- [PROPOSAL_UX_STYLING.md](../proposals/PROPOSAL_UX_STYLING.md) — Future styling (to be created)
