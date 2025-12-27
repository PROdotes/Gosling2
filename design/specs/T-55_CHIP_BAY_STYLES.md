# T-55 Spec: The Chip Bay (Visual Polish)

**Artist**: Bob Ross (Antigravity)
**Status**: DRAFT (On the Easel)
**Goal**: Turn the `NeonChip` placeholders into glowing, tactile data cartridges without fetching complex SVGs.

## 1. The Canvas (Current State)
*   **Location**: `FilterWidget.py` (Top Section).
*   **Logic**: `FlowLayout` holds `QPushButton`s named `#NeonChip`.
*   **Current Look**: Unstyled (Default Qt gray buttons).
*   **Target Look**: High-Tech Data Cartridges.

## 2. The Palette (QSS Strategy)
We will use a "Pro Audio" aesthetic: Dark, matte, low-fatigue.

### A. The Container (`#ChipBayScroll`)
*   **Background**: Transparent.
*   **Margins**: `4px` top/bottom.

### B. The Chip (`#NeonChip`)
The "Data Tag". Not a lightbulb.

*   **Shape**: Rounded Pill (Radius: `12px`).
*   **Base Style (Inactive)**:
    *   **Background**: `#222` (Dark Grey - Distinct from black bg).
    *   **Border**: `1px solid #333` (Subtle definition).
    *   **Text**: `#BBB` (Light Grey - Readable but not shouting).
*   **Active Style (Hover/Interaction)**:
    *   **Background**: `#2A2A2A` (Slight lift).
    *   **Border**: `1px solid #FF8C00` (Safety Orange) or `#D81B60` (Magenta) - Depending on context later.
    *   **Text**: `#FFF` (Bright White).
*   **The "Close" Indicator**:
    *   The `×` should be standard text color, turning Red (`#FF5252`) only when hovering directly over the chip (implies "Click to Remove").

### C. The Jingle Pads (Category Pills)
*   **Purpose**: These are "Tabs" or "Sources".
*   **Style**: Rectangular with rounded corners (4px). Left aligned in the header.
*   **Visual Separation**: They sit in the header; Chips sit in the flow below.

## 3. The Composition (Layout Tweaks)
*   **Spacing**: `FlowLayout` spacing: `6px`.
*   **Size**: Fixed height: `24px` (Compact). Font size: `9pt` (Crisp).

## 4. Execution Plan
1.  **Brush Work**: Update `theme.qss` with `#NeonChip` styles.
2.  **Detail Work**: Update `FilterWidget.py` logic to set the correct `hspacing` (if hardcoded).
3.  **Varnish**: Launch and verify the "Glow".
