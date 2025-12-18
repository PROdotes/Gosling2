# Type Tabs

**Task ID:** T-01  
**GitHub Issue:** #6  
**Layer:** UI  
**Score:** 15  
**Status:** 🟢 Next

---

## Summary

Filter library by content type using a horizontal tab bar.

## Requirements

- Tab bar above library: `All`, `Music`, `Jingles`, `Commercials`, `Speech`
- Clicking a tab applies `WHERE TypeID = X` filter
- Persist last-used tab in SettingsManager

## Implementation

- Add `QTabBar` or `QButtonGroup` above `LibraryWidget`
- Connect tab change signal to `QSortFilterProxyModel`
- Store selection in settings

## Checklist

- [ ] Add tab bar widget to library header
- [ ] Connect to proxy filter
- [ ] Persist selection in settings
- [ ] Add "All" option that clears filter

## Links

- [PROPOSAL_LIBRARY_VIEWS.md](../PROPOSAL_LIBRARY_VIEWS.md)
