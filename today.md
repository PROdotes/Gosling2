# 2026-01-01 - New Year Session

## 📌 Context
- **Status**: Fresh start for the new year.
- **Focus**: Accessibility and Core Workflows.

## 📅 Pending Features for Today
- [ ] **T-84: Primary Import Button** (UI Visibility).
      - Add a dedicated button to Import/Add Files in the main UI (Header/TitleBar) to avoid relying solely on Drag&Drop or Context Menus.
- [ ] **T-85: Mini Playlist Duration** (Polishing).
      - Display total playlist duration at the bottom of the Mini Playlist.
      - *Note*: Needs checking (design/feasibility).
- [ ] **T-86: Rename Rules Audit**.
      - Investigate "something feels off" with renaming logic. Check separators, compilation handling, and path generation.
- [ ] **T-87: Fix Ghost Hover**.
      - "Ghost amber bar" remains on table when mouse leaves. Need to clear `_hovered_row` on Viewport Leave event.
- [ ] **T-88: Phantom Scroll Bug**.
      - "Table sometimes scrolls right... mouse was still".
      - Suspect stuck drag state or AutoScroll triggering falsely. Need to check `setAutoScroll(False)` toggle feasibility.

## ✅ Completed Today
- (None)

## 🚧 Next Steps
- T-84 Planning.

## ⚠️ Known Issues / Warnings
- None currently active.
