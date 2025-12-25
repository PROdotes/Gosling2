# 🎨 UX/UI Constitution: Radio Automation vs. Consumer Apps

**Philosophy**: Gosling2 is a **Professional Broadcast Workstation**, not a generic player. It bridges the gap between the high-efficiency density of 2000s-era radio tools (like PlayIt Live) and the refined aesthetics of the 2020s. 

### THE "PLAYIT" CONTRAST:
Legacy radio apps are functional but clunky; they often hide metadata editing behind multiple windows ("Hoops"). Gosling2 kills the hoops by keeping the **Inspector (Editor)** as a permanent, first-class citizen of the layout.

---

## 📻 The "Radio Automation" Axioms
1.  **Status is Sovereign**: The user must know if a track is "Ready" (Done) or "Broken" (Incomplete) without clicking on it.
2.  **Density > Breathability**: Every pixel should serve a purpose. Large gaps of empty space are wasted metadata.
3.  **Correctness > Convenience**: The UI must yell (Yellberus) when data is wrong. SILENT failures are unacceptable in a broadcast environment.
4.  **Live-First (DJ Mode)**: 90% of the session is about the **Now** and the **Next**. Visualizing cues, hooks, and the upcoming log is the primary job of the interface.
5.  **Sub-Minute Search**: The Catalog must enable a multi-field filter (e.g., Mood:Upbeat + Genre:Pop + 90s) in under 60 seconds.

---

## 🎧 The DJ Mode Hierarchy

1.  **The Pulse (Now Playing)**: Big waveform/progress bar with Cue/Hook markers. This is the sun the rest of the UI orbits.
2.  **The Log (What's Next)**: A high-density list of the upcoming 5-10 songs. Must support rapid drag-and-drop reordering.
3.  **The Catalog (Search)**: A "No-Friction" library interface that handles complex queries instantly.
4.  **The Inspector (Editing)**: A support bay. It stays out of the way until a data error is spotted, then it becomes an immediate surgery room.

---

## 🔭 The Vision vs. The Reality (Dec 25, 2025)

| Feature | Current Reality | The "Pro" Vision |
| :--- | :--- | :--- |
| **Tab Bar** | Functional standard tabs. | **Pill Buttons**: High-contrast, custom QSS buttons (less browser-y). |
| **Library Table** | Standard grid view. | **Airy Data-Grid**: Remove vertical grid lines, use alternating row colors and custom height for "luxury density." |
| **Status Icons** | Checkboxes (Done/Active). | **Status Pills**: Colored status indicators (Green "AIR", Red "ERR", Yellow "RAW"). |
| **Player Bar** | Minimalist/Spotify-like. | **Deck View**: Larger timers, "Time to Outro" countdowns, big "Skip" button (The "Panic" Button). |
| **Metadata Panel** | Vertical stacking lists. | **The Inspector**: High-density Relational Editor with integrated Album Manager (T-46). |
| **Grid Styling** | Excel-style grid lines. | **Blade-Edge Rows**: 0px vertical grid, 1px horizontal separator, fixed 26px height. |

---

## 🏗️ The Modular Layout (The Conversion)

Gosling2 will shift from a fixed 3-column layout to a **Duality Dashboard**:

1.  **The Catalog (Left Collapsible)**: Navigation for the long-tail library.
2.  **The Stage (Center)**: The Library search results and item management. 
3.  **The Live Log (Integrated)**: The scrolling sequence of What's Playing vs. What's Next. In Gosling2, this is the persistent **Playlist Widget**.
4.  **The Inspector (Right Permanent)**: The metadata "surgery room." No sub-windows, no dialogs for basic edits. One click = Immediate Save-ability.
5.  **The Master Deck (Bottom Control Surface)**: High-visibility transport and timing.

---

## 🎨 Aesthetic Goal: "Current-Year Utility"
*   **No Clutter**: Avoid the "Windows XP" look of boxy borders and grey gradients.
*   **High Contrast**: Deep blacks (`#121212`) and sharp accents (`#D81B60`).
*   **Blade-Edge Density**: Data rows are tight (`26px`) but typography is modern (`Segoe UI`).

---

## 🔗 Relational Widget Standards (The Future)

To move away from "Free-Text Hell," the UI must transition to **Relational Components**:

1.  **Tag Chips (Category-Based)**: 
    *   Tags (Genre, Mood, Decade) must be rendered as **Pills/Chips**.
    *   **Colors**: Pills should be tinted by category (e.g., `Genre` = Blue, `Mood` = Orange) using the `id:name:category` DB structure.
2.  **Entity Pickers (Albums/Publishers)**:
    *   Instead of a text box, these use a **Picker Button**. 
    *   Clicking opens the relational manager.
    *   The UI must provide a "Quick-Clear" (X) and "Quick-Add" (+) shortcut within the field area.

---

## 📐 Pro-Density Specs (QSS Reference)

*   **Row Height**: `26px` (Tight but readable).
*   **Font**: `Segoe UI Semibold` for headers, `Segoe UI` for cell data.
*   **Colors**: 
    *   Base: `#121212` (Carbon)
    *   Row Alt: `#181818`
    *   Accent: `#0078D4` (Logic Blue) or `#D81B60` (Vesper Pink)
*   **Grid**: `verticalGridLine: 0px`, `horizontalGridLine: 1px #222`.

---

## 🔄 Handoff Context (For Tomorrow or Next Agent)
*   **Where we are**: We just finished a major "Cleanup" move (Import/Scan/Refresh are now in the context menu; "Show Incomplete" is in the filter sidebar).
*   **The Struggle**: The app currently feels "part Spotify, part Spreadsheet."
*   **The Next Move**: Tackle **T-46 (Proper Album Editor)** but with an eye toward the **Pro Studio** aesthetic—less generic input fields, more "Control Surface" inputs.

> **Note to LLM**: If you are picking this up, READ `METADATA_CONSTITUTION.md` first. Always respect the Yellberus Registry—it's the only thing keeping this radio station from going silent.
