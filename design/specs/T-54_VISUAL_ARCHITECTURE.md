# T-54: Visual Architecture & Layout (Vesper Revision)

## 1. Core Philosophy
*   **Intuitive & Readable**: High contrast. No "gray walls of text".
*   **Context-Sensitive**:
    *   **DJ Mode**: Focus on "What's Playing / Next / Previous".
    *   **Edit Mode**: Focus on "Clear Data Entry".

## 2. The Layout Topology (3-Column)

### A. LEFT: Archive (Fixed)
*   **Filter Tree Widget**: Standard navigation.
*   **Future**: Could be toggled with a "Crate" or "Jingle" view, but stable for now.

### B. CENTER: The Stage (Variable)
*   **Top**: App Header (Search, System Buttons).
*   **Middle**: `LibraryWidget` (Table). Flexible height.
*   **Bottom ("The Chin")**: **Jingle Pad Grid** (Toggleable Drawer).
    *   *Default*: Hidden (Height 0).
    *   *Active*: Slides up (Height ~200px), stealing space from Table.
    *   *Layout*: **Side-Stack Architecture** to save vertical space.
        *   **Left Strip**: Vertical Bank Selectors `[1][2][3][4]` + Config `[⚙️]`.
        *   **Main Area**: 16-Pad Grid (4x4) for instant FX.

### C. RIGHT: The Command Deck (Toggle Stack)
The Right Panel is a vertical layout where widgets show/hide based on the Header Toggles.

#### The Control Header
*   **Left (Small)**: `[ H ]` -> Toggles **History Log**.
*   **Center (Big)**: `[ SURGERY MODE ]` -> Toggles **Editor Form**.
*   **Right (Small)**: `[ = ]` -> Toggles **Compact Playlist**.

#### The Stack Zones
*   **Zone 1 (Top)**: `HistoryWidget`. Visible if `[H]` is active.
*   **Zone 2 (Middle)**: `SidePanelWidget`. Visible if `[SURGERY]` is active.
*   **Zone 3 (Bottom)**: `PlaylistWidget`. Always visible.
    *   **Constraint**: Must maintain `MinimumHeight` (~150px, approx 3 rows) to ensure upcoming tracks are never hidden by the Editor/History.

#### The Command Footer
*   **Placement**: Bottom of Right Panel.
*   **Row 1**: Transport (`Prev`, `Play`, `Stop`, `Next`).
*   **Row 2**: Transitions (`Cut`, `Fade`, `[Duration]`).

### D. BOTTOM: The Bridge (Global Scrubber)
*   **Placement**: Absolute bottom of the window (Footer), spanning Left+Center columns.
*   **Content**: Scrubber Bar + Time + Waveform (Future).
*   **Note**: Does *not* contain Transport Buttons (they moved to Right).

## 3. State Persistence (The "Smart Workspace")
The application must remember window/splitter states **per Mode**.
*   **Editor Mode State**: User likes Big Editor (70%), Small Playlist (30%).
*   **DJ Mode State**: User likes Small History (20%), Big Playlist (80%).
*   **Action**: When toggling `[LOG] <-> [EDIT]`, the system saves the current splitter position for the *exiting* mode and restores the saved position for the *entering* mode.

## 4. Implementation Plan
1.  **Refactor MainWindow**:
    *   Implement `RightVerticalSplitter`.
    *   Implement `TerminalHeader` with `[LOG | EDIT]` Segmented Control.
    *   Wire logic to swap Zone 1 widget.
2.  **Persistence Layer**:
    *   Update `SettingsManager` to store `window/splitter/log` and `window/splitter/edit`.
3.  **The Chin (Deferred)**:
    *   Note: While defined here, the "Chin" (Center Jingle Drawer) is technically T-55. We focus on the Right Panel (T-54) first to avoid destabilizing the Library Table today.

## 5. Visual Targets
*   **Banana Image**: Reference for "Editor" look (Boxed fields, Neon borders).
*   **Vesper Dark**: Deep charcoal backgrounds, Orange/Pink accents.

## 6. Integration Protocol (The Facade)
To avoid "wiring spaghetti," `RightPanelWidget` acts as a facade. `MainWindow` interacts only with the facade, not internal components.

### Inputs (Methods)
*   `update_selection(songs: List[Song])`: Passes selection to `SidePanel` (Editor).
*   `update_history(entries: List[LogEntry])`: Updates `HistoryDrawer`.
*   `set_mode(mode: str)`: Programmatically switch views ('log' | 'edit').

### Outputs (Signals)
*   `transport_command(cmd: str)`: 'play', 'pause', 'stop', 'next', 'prev'.
*   `transition_command(type: str, duration: int)`: 'cut' or 'fade'.
*   `playlist_action(action: str, data: Any)`: For drag/drop updates.

### Safety Protocols (User Feedback)
*   **Focus Policy**: All Buttons (Transport, Toggles) must have `Qt.FocusPolicy.NoFocus`. Clicking them should NOT steal focus from Search Bar or Editor.
