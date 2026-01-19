---
name: industrial-amber-design
description: Guidelines and components for the Gosling2 "Industrial Amber" workstation aesthetic.
---

# Industrial Amber Design System

This skill provides the aesthetic and technical guidelines for maintaining the "Industrial Amber" workstation look in Gosling2. Every UI component MUST follow these rules to ensure the "Premium Workstation" feel.

## 1. Style Primacy: No Hardcoded QSS

**CRITICAL RULE:** Never hardcode QSS strings (StyleSheets) directly in Python code. 
*   All styling must reside in `src/resources/theme.qss`.
*   Refer to components by their `objectName` (e.g., `self.setObjectName("CustomPanel")`) or `setProperty("class", "Class")`.
*   **Exception:** Dynamic properties that change at runtime (like setting a specific color from a user picker) may use inline styles if no other mechanism exists.

## 2. Palette Primacy: theme.qss over constants.py

**CRITICAL RULE:** `src/resources/constants.py` is for **LOGIC FALLBACKS** and internal code-only colors (like table delegates). It must **NEVER** be used to style UI components.
*   The source of truth for all visual colors is `theme.qss`.
*   If you need a specific Amber tone, use the CSS class or ID defined in `theme.qss`.
*   Do not import `constants` just to get `#FFC66D` for a `setStyleSheet` call.

## 3. Core Palette (Logic Fallbacks Only)

| Element | Color | Usage |
| :--- | :--- | :--- |
| **Amber** | `#FFC66D` | Primary accent, text, active signals, glowing controls. |
| **Muted Amber** | `#FF8C00` | Secondary highlights, warnings, tactical data. |
| **Magenta** | `#FF00FF` | Critical buttons, destructive actions, surgical focus. |
| **Cyan** | `#00E5FF` | Unprocessed data, cloud/virtual sources, metadata previews. |
| **Red** | `#FF4444` | Errors, raw WAV files, invalid states. |
| **Void** | `#000000` | Main background, chassis, depth. |

## 2. Component Factory usage

ALWAYS use the `GlowFactory` (found in `src.presentation.widgets.glow`) when creating interactive elements.

### GlowButton
Standard action button with halo effect.
```python
from ..widgets.glow import GlowButton
btn = GlowButton("COMMAND")
btn.setObjectName("PrimaryAction")
btn.setGlowColor("#FFC66D") # Default Amber
```

### GlowLineEdit
Search boxes and input fields.
```python
from ..widgets.glow import GlowLineEdit
search = GlowLineEdit()
search.setPlaceholderText("SCANNING...")
```

### GlowLED Status Indicators
Use these for mode signals (e.g., Prep Mode, Edit Mode).
```python
from ..widgets.glow import GlowLED
led = GlowLED(color="#FFC66D", size=10)
led.setActive(True) # Causes the "heartbeat" glow pulse
```

## 6. Layout and Spacing Guidelines

*   **The "Heavy" Separator:** Blocks of UI should be separated by 7px black bars. These should be `QFrame` widgets with the object name `SeparatorLine` or `HeavySeparator`.
*   **Splitters:** Use `QSplitter` for all main panels. Never hard-code panel widths unless they are "system buttons" or "islands".
*   **Borders:** Handled via `theme.qss`.

## 7. Typography Rules

*   **Primary:** Use **Bahnschrift Condensed** (fallback: "Segoe UI", sans-serif).
*   **Case:** Titles and button labels should be **ALL CAPS** (e.g., "RESTORE ON DRAG", "SAVE CHANGES").
*   **Branding:** Use the stacked label pattern for the application title to create the double-glow effect.

## 8. Industrial Details

*   **Glow Margins:** Interactive components should usually have a `4px` to `8px` glow margin to prevent the halo from being clipped by parents.
*   **Tooltips:** Use the `ReviewTooltip` or `GlowTooltip` for a dark-themed popover.
