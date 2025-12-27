# VISUAL_STYLE_GUIDE.md: "PROJECT GOSLING" (The Independent Operations Terminal)

## 1. Aesthetic Philosophy
*   **Archetype**: "Surgical Pro-Audio HUD" / "Hardware Data Rack".
*   **Core Logic**: The app is not a piece of software; it is a physical console with screens. It is built to be used for 8-hour shifts without eye strain.
*   **Keywords**: Matte, Modular, High-Contrast, Industrial, Low-Fatigue, Structural.
*   **Anti-Patterns**:
    *   **No Rounded Pills**: We use sharp, industrial 0px corners for all data modules.
    *   **No "Software Glow"**: Glow is reserved only for active hardware indicators (LEDs).
    *   **No Warning Colors for UI**: We avoid "Safety Orange" for standard navigation; it's too aggressive.

## 2. Color Palette
**The Gold Standard**: If it's on the screen, it's either **Material** (Structure) or **Signal** (Data).

### The Material Stack (Structure)
*   `#0A0A0A`: **Void Background** (The chassis floor). 
*   `#1A1A1A`: **Root Chassis** (The faceplates for primary modules/headers).
*   `#111111`: **Recessed Sub-Rack** (Sub-groupings/Branch level).
*   `#222222`: **Border/Divider** (Structural separation).

### The Signal (Interaction)
*   `#FFC66D`: **Warm Amber** (The "Incandescent Bulb" signal). Primary focus and selection color.
*   `#E0E0E0`: **Active Data** (White text for selected or high-priority items).
*   `#888888`: **Recessed Data** (Grey text for background/inactive data).

### Semantic Logic (Track Types)
*   **Music**: `#2979FF` (Electric Blue).
*   **Jingle**: `#D81B60` (Neon Magenta).
*   **Speech/Voice**: `#FFC66D` (Warm Amber - Shared with system signal).
*   **Commercial**: `#43A047` (Profit Green).
*   **Stream**: `#7E57C2` (Digital Purple).

## 3. The "Gosling Signature" Rules
### Rule A: The Signal Rail
We never use full-box background highlights for selection. Selection is indicated by a **3px Signal Rail**:
*   **Horizontal (Tabs/Pills)**: 3px Bottom Underline.
*   **Vertical (Trees/Tables)**: 3px Left "Spine".

### Rule B: Hardware LEDs
All binary toggles (Checkboxes) are rendered as **Physical LEDs**:
*   **Off**: A dark recessed socket.
*   **On**: A glowing Warm Amber filament with a subtle radial glow.

### Rule C: Structural Depth
The UI follows a **3-Layer Depth** model to prevent flat-data fatigue:
*   **Top Level**: Solid #1A1A1A faceplates (Modules).
*   **Mid Level**: Recessed #111111 tracks (Sub-groupings).
*   **Item Level**: Transparent background (Surgical Data).

## 4. Typography
*   **UI Labels**: `Bahnschrift Condensed`. High verticality, space-efficient, professional.
*   **Data Readouts**: `Consolas` (or equivalent Monospace). Used for Timecodes, BPM, Key, and technical metrics.
*   **Hierarchy**: Headers are **Bold White**, Items are **Recessed Grey**.

## 5. UI Components
*   **Pills & Chips**: These are "Data Modules". Sharp corners, 1px border, matte finish.
*   **The Mission Deck (Table)**: Horizontal scanlines only. No vertical grid lines. Selection is a dynamic rail matching the Track Type color.
*   **The Command Deck (Right Panel)**: Should look like a stack of server rack units. Each section is a separate "Blade".
