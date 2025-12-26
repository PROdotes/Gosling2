# Handover: Surgical Right-Channel Refactor (T-49 Phase 2)

## 📍 Context
The current Right Channel uses a `QStackedWidget` with Tabs. This is a "Consumer" layout. The "Workstation" spec (T-49) requires a dynamic split where the Editor and Playlist coexist in **Surgical Mode**.

## 🎯 Objective
Pivot the Right Channel from "Either/Or" (Tabs) to "Focus-Shift" (Dynamic Split).

### 1. The Logic States
- **Playout Mode (Default)**:
    - `PlaylistWidget` takes **100%** height.
    - `SidePanel` is **Hidden**.
    - Purpose: High-fidelity log monitoring during automation.
- **Surgical Mode (Editing)**:
    - `SidePanel` (Editor) takes the **Top 70%** of the height.
    - `PlaylistWidget` (Mini-Log) is squished to the **Bottom 30%**.
    - Purpose: Fast metadata correction while keeping the "Next 3" tracks in sight.

### 2. Technical Implementation (MainWindow.py)
1. **Remove `QStackedWidget` and `QTabBar`** from the `RightSurgicalPanel`.
2. **Implement a Nested Vertical Splitter** inside the Right Panel:
   - Top: `SidePanelWidget`
   - Bottom: `PlaylistWidget`
3. **Mode Toggle**:
   - Replace the tabs with a single "SURGICAL EDITOR" neon button (or trigger it automatically on Library selection).
   - Use `self.right_splitter.setSizes([700, 300])` for Surgical.
   - Use `self.right_splitter.setSizes([0, 1000])` for Playout.
4. **Mini-Log View**:
   - Add a property to `PlaylistWidget` (e.g., `set_mini_mode(bool)`).
   - When `True`, the delegate should hide album art/extra detail and only show Title/Artist/Time in a single dense row.

### 🧩 Painless Layout Transition
To avoid the "Layout PITA" of manual widget math:
- **Nested Splitter**: The `RightSurgicalPanel` will use a vertical `QSplitter` containing the Editor (Top) and Playlist (Bottom).
- **The Shift**: Transitioning from Playout to Surgical will be a single `setSizes([700, 300])` call.
- **The Magic**: The `QSplitter` handles the complex animation/resizing of the widgets automatically. We only change the *drawing* style of the playlist rows when it enters "Mini" mode.


## 🎨 Visual Notes
- The **Overlay Resize Grip** must still stay in the absolute bottom-right corner.
- The **Neon Pink top-border** on the Playback Deck must align perfectly with the bottom of the Mini-Log when in Surgical mode.

## 🚀 Next Steps (Day 2)
- [ ] Refactor `MainWindow._init_ui` for the nested right-splitter.
- [ ] Implement the `Mode` toggle signal.
- [ ] Update `PlaylistItemDelegate` to support a "Compact" view type.

## ⚙️ Hardware Unlocking (T-52)
The next session must also address the "Hardcoded Shackles":
- **Database Path**: Currently fixed to `sqldb/gosling2.sqlite3` in `DatabaseConfig`. Must be moved to `SettingsManager`.
- **Root Directory**: Currently defaults to `C:/Music`. Needs a UI selector.
- **Rules Config**: Externalize renaming/moving rules so flowchart brain can rest knowing logic is configurable.

## 🧠 Surgical UX Foundations
The "Workstation" feel is the priority. Forms must not feel like "Data Entry":
1. **Album Editor**: Zero-dialog workflow. Inline search/assign with massive cover art confirmation.
2. **Tag Editor**: High-density "Chip" cloud. One-click toggle, no deep menus.
3. **Rollback Log (History)**: Needs to look like a **Surgical Audit**. Chronological, "Terminal-style" entries. 
   - UX: Hovering a history entry should highlight what *changed* in the Library/Editor. 
  - Status: "Green for Saved", "Yellow for Staged".

## ⌨️ Input Philosophy: The Pro vs. The Mouse
A core design rule for all new widgets (Album/Tag Editors):
- **Keyboard Parity**: Everything MUST have a shortcut (Legacy pros like `Ctrl+R`).
- **Mouse/Context Parity**: Everything MUST be accessible via Right-Click or clear UI buttons (Modern/Touch).
- **Goal**: Multicheck filtering should act as a "Visual Search," reducing the mental load of the text search bar.

## 🎧 Auditioning & The Back Button Dilemma
*Note: The current Playback Deck was a "Consumer Rush." We need to pivot it to Workstation logic.*
1. **The "Back" Button**: Radioactive automation doesn't "go back" in a live log. We need to decide if that button becomes a "Restart Track" or a "Jump to Previous Log Entry."
2. **Surgical Audition (0.1 Priority)**: 
   - Problem: Currently, to hear a song, you must `Add to Playlist -> Play -> Scrub`.
   - Goal: Implement a **"Quick Listen"** mode. 
   - Vision: Double-clicking or a specific "Audition" key in the Library should load the song into the Master Deck (or a hidden preview deck) instantly for scrubbing, without requiring a playlist slot.
   - Purpose: Fast metadata checking/cue-finding.



## 🔍 Multicheck Filtering (T-55)
Assessment for the "Multipass" filter request:
- **Complexity**: 3/10 (Mid-Easy).
- **Technical Pivot**: Move from DB re-queries (current) to a "Smart Proxy Model" approach. 
  - Instead of re-fetching rows, the `LibraryFilterProxyModel` should track a `ActiveFilters` dictionary.
  - UI: `FilterWidget` needs to enable checkboxes (`ItemIsUserCheckable`).
- **Logic**: Filters should be **Additive** (OR within a category, AND across categories).
  - e.g., (Genre: Rock OR Jazz) AND (Year: 1994).
- **UI Element: The "Chip Bay"**: Add a horizontal-wrap area (QFlowLayout style) at the bottom of the Filter sidebar.
  - Every checked item in the tree appears here as a "Neon Chip" (e.g., [x] 1994).
  - Clicking the [x] on a chip removes the filter (unchecks the tree item).
  - This solves the "Where am I?" problem with deep trees.



---
*Signed: Antigravity (Protocol Vesper)*
