# Proposal: Unified Status Deck (T-92)

## 1. Overview
The **Status Deck** is a specialized, immutable column at **Index 0** of the Library Table. It consolidates multiple status indicators (Active State, File Type, Virtual Status, Dirty State) into a single, high-fidelity visual element ("The Chip").

## 2. Visual Language
The Chip uses **Shape** to indicate *File Type* and **Color/Glow** to indicate *State*.

### A. Shapes (File Type)
| Shape | Meaning | Context |
| :--- | :--- | :--- |
| **Circle** | Standard Audio | Physical MP3/AAC files. The baseline. |
| **Square** | Virtual Container | Encapsulated files (ZIP/RAR). |
| **Triangle** | Staged / Raw | WAV/FLAC files requiring conversion. |

### B. Colors (Status)
| Color | Hex | Meaning |
| :--- | :--- | :--- |
| **Amber** | `#FFC66D` | **Standard**. Ready to play. |
| **Cyan** | `#00E5FF` | **Virtual**. Reading from archive. |
| **Red** | `#FF4444` | **Attention**. needs conversion (WAV) or error. |
| **Magenta** | `#FF00FF` | **Dirty**. Unsaved changes (Overlay Dot). |

### C. States (Activity)
| State | Visual Style |
| :--- | :--- |
| **Active (ON)** | Solid shape with radial glow (Halo). |
| **Inactive (OFF)** | Hollow outline (Ring) or dimmed fill (30% opacity). |
| **Playing** | Pulse animation or Center Icon (Speaker). |

## 3. Interaction
*   **Left Click**: Toggles the `is_active` state (ON/OFF).
*   **Right Click**: Context Menu (Convert, etc.).
*   **Drag & Drop**: **Disabled**. This column is anchored.

## 4. Technical Implementation

### A. `GlowLED` Refactor
Update `src/presentation/widgets/glow/led.py` to support drawing shapes.
```python
def draw_led(painter, rect, color, active, shape='CIRCLE', ...)
```

### B. `LockedHeader` (Subclass `QHeaderView`)
*   `setSectionResizeMode(0, Fixed)` (**CRITICAL**: Prevents resizing).
*   `resizeSection(0, 40)` (Hardcoded width ~40px).
*   Override `mousePress/Move` to prevent dragging Index 0.
*   Prevent dropping other columns onto Index 0.

### C. `LibraryDelegate`
*   Remove "Active" column logic.
*   Implement `paint()` for Column 0 using `GlowLED.draw_led`.
*   Logic to map `Song` properties to Share/Color.

### D. `LibraryWidget`
*   Insert "Status" column at Index 0 in Model.
*   Map clicks on Column 0 to `_toggle_active` logic.
