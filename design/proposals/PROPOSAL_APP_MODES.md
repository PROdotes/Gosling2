---
tags:
  - layer/ui
  - layer/core
  - domain/audio
  - status/planned
  - type/architecture
  - size/medium
links:
  - "[[PROPOSAL_ONAIR_UI]]"
  - "[[PROPOSAL_LIBRARY_VIEWS]]"
---
# Architectural Proposal: Application Context Modes

## Objective
Implement a high-level "Context Switch" for the entire application, optimizing the UI for distinct workflows: **Archiving** (Data Entry) vs. **Broadcasting** (Performance).

## 1. The Contexts

### 🟢 Edit Mode (The "Archivist")
- **Primary Goal:** Data integrity, detailed auditing, complex modifications.
- **UI State:**
    - **Library:** Detail List View (All columns visible).
    - **Side Panel:** Expanded Metadata Editor.
    - **Interaction:** Right-click menus enabled, double-click edits enabled.
    - **Safety:** High. Staging warnings active.

### 🔴 Broadcast Mode (The "On-Air")
- **Primary Goal:** Stability, visibility, speed.
- **UI State:**
    - **Library:** Compact List or Art Grid (High visibility).
    - **Side Panel:** Collapsed (or replaced by "Next Up" Queue).
    - **Visible Columns:** Title, Artist, Duration, Year, Intro/Outro (Timing focus).
    - **Interaction:** One-click play/cue. "Dangerous" editing features disabled/hidden.
    - **Safety:** Critical. Modal dialogs suppressed.

## 2. Implementation Strategy
- **State Management:** `AppController` maintains a `current_mode` Enum.
- **Observer Pattern:** UI components (Library, SidePanel, Player) subscribe to `mode_changed` signals and adapt their layout/visibility accordingly.
- **Persistence:** Save the last used mode in `SettingsManager`.

## 3. Visual Differentiation
- The application header or status bar should clearly indicate the current mode (e.g., a green vs red accent line) to prevent accidental edits during a broadcast.
