# Spec: T-54 Surgical Layout (Workstation Mode)

## 1. Problem Statement
The current interface uses a "Consumer" paradigm where the user can see *either* the Playlist *or* the Editor, but not both. This prevents the core workflow of "checking the log while fixing metadata."

## 2. The Solution: "Surgical Mode"
Pivot the Right Panel from a Tabbed Stack (`QStackedWidget`) to a Dynamic Vertical Split (`QSplitter`).

### 2.1 Layout Structure
- **Container**: `RightSurgicalPanel` (QFrame)
- **Layout Manager**: `QVBoxLayout` -> `QSplitter` (Vertical)
- **Component A (Top)**: `SidePanelWidget` (Metadata Editor)
    - Default Height: 70%
    - Visibility: Toggled by Mode.
- **Component B (Bottom)**: `PlaylistWidget` (The Log)
    - Default Height: 30%
    - Appearance: In "Surgical Mode", this switches to a compact "Mini-Log" view (Artist - Title - Time only).

### 2.2 Functional Modes
The user can toggle between two view states:

1.  **Playout Mode (F1)**
    *   **Editor**: Hidden (Height 0%).
    *   **Playlist**: Full Height (100%).
    *   *Use Case*: Automated playout monitoring.

2.  **Surgical Mode (F2)**
    *   **Editor**: Visible (Top).
    *   **Playlist**: Compact (Bottom).
    *   *Use Case*: Active database maintenance while live.

### 2.3 Visual Components (The "Neon" Update)
- **Library Header**: Replace `QTabBar` with "Category Pills" (`TypePillsWidget`).
    - Buttons: `ALL`, `MUS`, `JIN` (Jingles), `COM` (Commercials), `SP` (Speech), `STR` (Stream).
    - Behavior: Exclusive filter toggles.
- **Filter Sidebar**: Add "Neon Chip Bay" at the bottom for active multicheck filters.

## 3. Implementation Plan (Recovery)
1.  **Refactor MainWindow**: Replace the right-hand `QStackedWidget` with the `QSplitter` setup described above.
2.  **Fix Component Visibility**: Ensure `SidePanelWidget` and `PlaylistWidget` are correctly added to the splitter.
3.  **Implement Toggle Logic**: Connect the "Editor" button (top right) to toggle between Playout/Surgical modes.
