# T-54 EXECUTION PLAN: The Operation

This document details the step-by-step refactoring process for the Right Panel Architecture ("The Command Deck").

## 1. COMPONENT FABRICATION (`right_panel_widget.py`)
**Goal**: Create the self-contained UI module matching `T-54_VISUAL_ARCHITECTURE.md`.

*   [x] **Imports**: Ensure all Qt widgets (`QSplitter`, `QComboBox`, etc.) and dependencies (`HistoryDrawer`, `SidePanelWidget`, `PlaylistWidget`) are imported.
*   [x] **Class `RightPanelHeader`**:
    *   Implement Toggles: Log `[H]`, Edit `[SURGERY]`, Compact `[=]`.
    *   **Safety**: Apply `setFocusPolicy(Qt.FocusPolicy.NoFocus)` to all buttons.
*   [x] **Class `RightPanelFooter`**:
    *   Row 1: Transport (`Prev`, `Play`, `Stop`, `Next`).
    *   Row 2: Transitions (`Cut`, `Fade`, `[Duration]`).
    *   **Safety**: Apply `setFocusPolicy(Qt.FocusPolicy.NoFocus)`.
*   [x] **Class `RightPanelWidget`**:
    *   **Layout**: Vertical Box [Header -> Splitter -> Footer].
    *   **Splitter**: Vertical Orientation.
        *   Zone 1: `HistoryDrawer` (Default: Hidden).
        *   Zone 2: `SidePanelWidget` (Default: Hidden).
        *   Zone 3: `PlaylistWidget` (Default: Visible).
    *   **Constraints**: `playlist_widget.setMinimumHeight(150)` (The 3-Song Rule).
    *   **Facade Methods**:
        *   `update_selection(songs)` -> Delegates to `editor.set_songs()`.
        *   `set_mode(mode)` -> Toggles visibility of zones.
    *   **Signals**: Define `transport_command(str)`, `transition_command(str, int)`.

## 2. MAIN WINDOW INTEGRATION (`main_window.py`)
**Goal**: Replace the old Tabs with the new Command Deck.

*   [x] **Initialization (`_init_ui`)**:
    *   Remove `QTabWidget` (Right Tabs).
    *   Initialize `self.right_panel = RightPanelWidget(...)`.
    *   Pass required services: `library_service`, `metadata_service`, `renaming_service`, `duplicate_scanner`.
    *   Add `self.right_panel` to `self.main_splitter`.
*   [x] **Wiring (`_setup_connections`)**:
    *   **Input**: `self.library_widget` selection signal -> `self.right_panel.update_selection`.
    *   **Output**: `self.right_panel.transport_command` -> `self.playback_service` methods (`play`, `pause`, etc).
    *   **Output**: `self.right_panel.transition_command` -> `self.playback_service` (Crossfade logic).
*   [x] **State Persistence**:
    *   Load/Save logic needs to include `right_panel` splitter state.

## 3. CLEANUP (Post-Integration)
*   [x] **Verify**: Run application. Check "Focus Trap" (hit Spacebar after clicking buttons).
*   [x] **Duplicate Buttons**: The Global Footer (Bottom) still has buttons.
    *   *Decision*: Leave them for now (Backup).
    *   *Future*: Remove them in T-53 Polish.

## 4. ROLLBACK STRATEGY
If the app fails to launch:
1.  Revert `main_window.py` to use `QTabWidget`.
2.  Comment out `RightPanelWidget` import.
