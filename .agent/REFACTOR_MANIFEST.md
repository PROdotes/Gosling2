# Refactor Manifest: Migrate Inline Styles to QSS

**Goal:** Remove all inline `setStyleSheet()` calls from Python code and move styling to `theme.qss`

**Date Started:** 2025-12-28

## Target Files

| # | File | Status | Receipt |
|---|------|--------|---------|
| 1 | `src/presentation/widgets/side_panel_widget.py` | **Done** | Removed L104-113, L249, L273, L316, L397-403, L583-592. Added setProperty("state") for dynamic pill. QSS: StatusPill, FieldLabel, FieldGroupLabel, AlbumPickerButton |
| 2 | `src/presentation/widgets/right_panel_widget.py` | **Done** | Removed STYLE_BTN_BASE, L46/99 setStyleSheet, L64/82/118/135/148 inline styles. Added objectNames + setProperty("class", ...) |
| 3 | `src/presentation/widgets/playback_control_widget.py` | **Done** | Removed STYLE_BTN_BASE, L90/134-154/161-163 setStyleSheet. QSS: PlaybackCommand, PlaybackPlayButton, LargeSongLabel, CoverBay, PlaybackTimer, PlaybackFadeCombo |
| 4 | `src/presentation/widgets/jingle_curtain.py` | **Done** | **Hard Standard reached.** All dynamic colors moved to semantic QSS ID selectors (#JingleButton_ads, etc). |
| 5 | `src/presentation/widgets/history_drawer.py` | **Done** | Removed L18-33 setStyleSheet block. QSS: QFrame#HistoryDrawer, QLabel#HistoryTitle |
| 6 | `src/presentation/widgets/filter_widget.py` | **Done** | **Hard Standard reached.** Semantic coloring moved to QSS selectors ([objectName^="Chip_..."]). |
| 7 | `src/presentation/dialogs/album_manager_dialog.py` | **Done** | Full dialog styling moved to global layer. Redressed for visibility. |
| 8 | `src/presentation/views/main_window.py` | **Done** | TerminalHeader, Separators, and PrepLog logic moved to QSS. |

## Inventory of setStyleSheet Calls

### side_panel_widget.py (6 calls)
- L104: btn_status base styling
- L249: group_label styling (FORCE BLUE)
- L273: field label styling (FORCE AMBER)
- L316: field label styling (FORCE AMBER)
- L397: album picker button styling
- L583: btn_status dynamic styling (READY/PENDING states)

### right_panel_widget.py (8 calls)
- L46: RightPanelHeader background
- L64: btn_edit font override
- L82: btn toggle base styling (STYLE_BTN_BASE)
- L99: RightPanelFooter background  
- L118: btn_play special styling
- L135: combo_fade styling
- L148: btn command button styling (STYLE_BTN_BASE)

### playback_control_widget.py (4 calls)
- L90: combo_fade styling
- L134: PlaybackDeck large stylesheet block
- L161: transport button styling
- L163: play button special styling

### jingle_curtain.py (5 calls)
- L21: title label styling
- L25: info label styling
- L30: JingleCard styling
- L59: JingleCurtain styling
- L75: curtain title styling

### history_drawer.py (1 call)
- L18: HistoryDrawer stylesheet block

### filter_widget.py (1 call - DYNAMIC)
- L570: NeonChip dynamic border color (semantic coloring)

### album_manager_dialog.py (6 calls)
- L29: dialog base stylesheet
- L63: title label styling
- L103: form_frame background
- L113: type label styling
- L116: combo type styling
- L153: label styling

### main_window.py (8 calls)
- L88: TerminalHeader stylesheet
- L112: dot/LED styling (dynamic color)
- L130: prep_btn styling
- L156: status_led base styling
- L165: btn styling
- L187/189: status_led dynamic states
- L261: top_separator styling
- L320: bottom_separator styling

## Post-Refactor Status: THE HARD STANDARD
- **Surgical Separation**: All Python UI logic is now strictly behavioral.
- **Zero Inline CSS**: `grep setStyleSheet src` returns only comments.
- **Semantic Coloring**: Colors are no longer passed as hex strings; they are derived in QSS from object names (e.g., `#JingleButton_ads`) or properties (e.g., `[objectName^="Chip_"]`).
- **Single Source of Truth**: Visual design is entirely encapsulated within `src/resources/theme.qss`.

## Final Audit
- All functional families (Primary, Toggle, Pill) are established in QSS.
- No trace of CSS strings remains in `src/`.
- Dynamic color-coding is preserved through static semantic identifiers.
