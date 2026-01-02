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
- [ ] **T-88: Investigate Pending Status**.
      - User reports "Pending Status might not be working". Verify Amber/Green logic for staged changes.
- [ ] **T-89: Missing Data View**.
      - "Opposite of pending": Show files that are missing required metadata (Artist, Title, etc.) - effectively an "Incomplete" filter.
- **Refactoring Debt (v0.2 Candidates)**:
  - **Dialog/Picker Duplication**: Consolidate `ArtistPickerDialog`, `PublisherPickerDialog`, etc. into a `DialogFactory`.
  - **ChipTray Abstraction Leak**: `ChipTrayWidget` exposes internal tuple structure `(id, label, icon...)` to consumers. It should handle simple string lists internally (`set_strings(["A", "B"])`) to avoid boilerplate.

## ✅ Completed Today
- (None)

## 🚧 Next Steps
- T-84 Planning.

## ⚠️ Known Issues / Warnings
- None currently active.
