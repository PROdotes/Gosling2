# GLOWUP V1 SPEC: "Industrial Broadcast Console"
**Created**: December 27, 2025  
**Status**: Active Design Document  
**Based On**: Concept V2 Mockup

---

## 1. GENERAL VISION

### 1.1 The Feeling
This is a **professional broadcast workstation** — not a consumer music player, not a web app. It should feel like:
- A physical mixing console or broadcast automation terminal
- Equipment you'd find in a radio station control room
- Something built for 8-hour shifts, not 5-minute sessions

### 1.2 The Aesthetic
**"Flat Industrial with Depth"** — We achieve the feel of physical hardware using only QSS-achievable techniques:
- **Gradients** for 3D depth (light direction: from below/front)
- **Glow effects** for active states (backlit buttons, LED indicators)
- **Subtle rounding** (2-4px radius) on interactive elements; scrollbars and LED indicators can be more rounded (6px, circular)
- **Matte surfaces** with subtle sheen, not glossy

### 1.3 The Principles
| Principle | What It Means |
|-----------|--------------|
| **Light Comes From Below** | Gradients are darker at top, lighter at bottom. Creates "backlit console" feel. |
| **Amber Is The Signal** | Warm amber (`#FFC66D`) is the ONE primary accent. It means "active," "selected," "attention here." All hovers default to amber unless the element is already magenta. |
| **Magenta Is Playback + Errors** | Neon magenta (`#D81B60`) is reserved for transport/playback controls AND error states (e.g., ISRC validation fail). |
| **Contrast Is King** | Labels must be readable. No more dark-gray-on-black. |
| **Signal Rails Over Fill** | Selection is indicated by edge accents (3px rails), not background fills. |
| **Type Distinction Is Subtle** | Semantic colors (Music=blue, Jingle=magenta) appear only on hover hints and selected item borders/chips. Don't flood the UI with color noise. Playlist items need visible type indicators. |

### 1.4 Group vs. Child Visual Hierarchy
In collapsible trees (Filter Panel), it must be obvious at a glance:
- **Groups** (collapsible headers) are visually distinct from **children** (leaf items)
- When collapsed, groups should NOT look like selected children
- Technique: Groups have bolder weight, larger height, and distinct border treatment (e.g., bottom border on groups, no border on children, OR different background tint)

---

## 2. COLOR SYSTEM

### 2.1 The Material Stack (Structure/Background)
These define the physical "chassis" of the UI.

| Token | Hex | Usage |
|-------|-----|-------|
| `--void` | `#050505` | Deepest recesses (input field backgrounds, inset areas) |
| `--floor` | `#0A0A0A` | Primary background (window, panels) |
| `--chassis` | `#111111` | Raised surfaces (button backgrounds, card bases) |
| `--rail` | `#1A1A1A` | Elevated panels, headers, dividers |
| `--border` | `#222222` | Structural borders, separators |
| `--border-hover` | `#333333` | Hover state borders |

### 2.2 The Signal Stack (Accent/Interaction)
These indicate state and draw attention.

| Token | Hex | Usage |
|-------|-----|-------|
| `--amber` | `#FFC66D` | Primary signal: selection, active states, primary buttons, text selection background |
| `--amber-hot` | `#FFD54F` | Intense amber: LED glow centers, pressed states |
| `--amber-muted` | `#AA8844` | Pressed/desaturated amber for button pressed tint |
| `--magenta` | `#D81B60` | Playback controls AND error states (validation failures) |
| `--magenta-hot` | `#FF4081` | Intense magenta: playback button hover, critical errors |

### 2.3 The Data Stack (Text/Content)
These are for reading.

| Token | Hex | Usage |
|-------|-----|-------|
| `--text-bright` | `#FFFFFF` | Active/selected item text, headers |
| `--text-normal` | `#E0E0E0` | Standard readable text |
| `--text-muted` | `#888888` | Secondary labels, inactive items |
| `--text-dim` | `#555555` | Placeholder text, disabled states |

### 2.4 Semantic Colors (Track Types)
Consistent across Category Buttons, Tag Pills, and table row rails.

| Type | Hex | Usage |
|------|-----|-------|
| Music | `#2979FF` | Electric Blue |
| Jingle | `#D81B60` | Neon Magenta |
| Speech | `#FFC66D` | Warm Amber |
| Commercial | `#43A047` | Profit Green |
| Stream | `#7E57C2` | Digital Purple |

### 2.5 Status Colors
| Status | Hex | Meaning |
|--------|-----|---------|
| Success/Done | `#00E676` | Bright green |
| Warning/Pending | `#FFC107` | Amber-yellow |
| Error/Invalid | `#FF5252` | Bright red |

---

## 3. TYPOGRAPHY

### 3.1 Font Stack
| Role | Font | Fallback |
|------|------|----------|
| Headers/Labels | `Bahnschrift Condensed` | `Agency FB`, `Segoe UI Semibold` |
| Body/Data | `Segoe UI` | `sans-serif` |
| Monospace/Readouts | `Consolas` | `Courier New`, `monospace` |

### 3.2 Scale
| Level | Size | Weight | Usage |
|-------|------|--------|-------|
| H1 (Panel Title) | 14pt | Bold | Side panel headers |
| H2 (Section) | 11pt | Bold | Group headers (e.g., "CORE METADATA") |
| Body | 10pt | Normal | Standard UI text |
| Small/Label | 9pt | Bold | Field labels, column headers |
| Micro | 8pt | Normal | Paths, timestamps, technical data |

### 3.3 Styling
- **All caps** for labels and headers (`text-transform: uppercase`)
- **Letter spacing**: 1-1.5px for headers
- **No italics** — they don't fit the industrial aesthetic

---

## 4. WIDGET SPECIFICATIONS

### QSS Selector Reference
Map of spec terms to actual `objectName` values in the codebase:

| Spec Term | QSS Selector | Location |
|-----------|--------------|----------|
| Filter Tree | `QTreeView#FilterTree` | Left sidebar |
| Library Table | `QTableView` + `#LibraryHeader` | Center panel |
| Category Buttons | `QPushButton#CategoryPill` | Top tab bar (Deck Buttons) |
| Tag Pills | `QPushButton#NeonChip` | Filter sidebar + Editor (removable tags) |
| Command Buttons | `QPushButton#CommandButton` | Filter header (ALL+, etc.) |
| Primary Button | `QPushButton#PrimaryButton` | Various |
| Save Button | `#SaveAllButton` | Side panel footer |
| Discard Button | `#DiscardButton` | Side panel footer |
| Mark Done | `#MarkDoneButton` | Side panel footer |
| Side Panel | `#RightSurgicalPanel` | Right panel container |
| Playback Deck | `#PlaybackDeck` | Bottom player |
| Section Headers | `#FieldGroupLabel` | Side panel groups |
| Field Labels | `QLabel[objectName="FieldLabel"]` | Side panel fields |

---

### 4.1 TreeView (Filter Panel)

#### Overall Feel
A **hardware channel strip** — each expandable group is a module in the rack.

#### Widget Container
```
Background: --floor (#0A0A0A)
Border-right: 1px solid --border (#222)
```

#### Group Headers (has-children items)
```
Height: 34px
Background: transparent
Text: --text-muted (#888) → --text-bright (#FFF) on hover
Font: 11pt, Bold, Uppercase
Padding-left: 12px
Border-bottom: 1px solid --border (#222)
```

#### Child Items (leaf nodes)
```
Height: 28px
Background: transparent
Text: --text-muted (#888) → --text-normal (#E0E0E0) on hover
Font: 11pt, Normal
Padding-left: 24px
Border-bottom: 1px solid --chassis (#111)
```

#### LED Indicators (Checkboxes)
```
Size: 10px × 10px
Border-radius: 5px (circular)
Border: 1px solid --border (#222)

Unchecked:
  Background: --void (#050505)
  Border-color: #222

Checked:
  Background: radial-gradient (solid colors, no transparency)
    center: #FFFFFF (hot filament)
    0.2: #FFE0B2 (warm glow)
    0.7: #FFC66D (amber)
    1.0: #452600 (dark outer edge)
  Border: 1px solid --amber-hot (#FFD54F)
  — Creates that "activated switch with amber bleeding through" feel
```

#### Branch Chevrons
```
Color: --text-dim (#555) → --text-muted (#888) on hover
Size: 8px
Style: Simple triangle (▶ collapsed, ▼ expanded)
```

---

### 4.2 TableView (Library Grid)

#### Overall Feel
**Mission control data display** — high density, scanline aesthetic.

#### Widget Container
```
Background: --floor (#0A0A0A)
Border: none
Grid-lines: horizontal only (1px --chassis)
```

#### Zebra Striping
```
Even rows: --floor (#0A0A0A)
Odd rows: #0F0F0F (subtle, not aggressive)
```

#### Column Headers
```
Height: 36px
Background: --floor (#0A0A0A)
Text: --text-dim (#666) → --text-muted (#888) on hover
Font: 10pt, Bold, Uppercase
Letter-spacing: 1.5px
Border-bottom: 1px solid --border (#222)
Border-right: 1px solid --rail (#1A1A1A)

Pressed state:
  Background: --amber
  Text: black
```

#### Row Selection
**Signal Rail technique** — NOT background fill.
```
Selected row:
  Background: transparent (or very subtle #0F0F0F)
  Left border: 3px solid --amber (#FFC66D)
  Text: --text-bright (#FFF)
```

#### Row Hover
```
Background: #0F0F0F
Text: --text-normal (#E0E0E0)
```

---

### 4.3 Buttons

#### The "Backlit Console Button" Technique
All buttons use the **light-from-below** gradient:

```
Default:
  Background: linear-gradient(top→bottom)
    0%: --chassis (#111)
    85%: #1A1A1A
    100%: #252525 (lighter at bottom = backlit)
  Border: 1px solid --border (#222)
  Border-bottom: 2px solid --border-hover (#333) (subtle underglow line)
  Text: --text-muted (#888)

Hover:
  Background: same gradient, slightly lighter values
  Border-bottom: 2px solid --amber (#FFC66D) (amber underglow)
  Text: --text-normal (#E0E0E0)

Pressed:
  Background: linear-gradient INVERTED (darker at bottom)
    0%: #1A1A1A
    100%: #080808 (light source "pressed in")
  Border-bottom: 1px solid --chassis (underglow disappears = light blocked)
  Text: --text-muted
```

#### Primary Action Buttons
```
Background: linear-gradient(top→bottom)
  0%: #CC9A50 (darker amber)
  85%: --amber (#FFC66D)
  100%: --amber-hot (#FFD54F) (glowing bottom edge)
Border: 1px solid --amber
Border-bottom: 3px solid --amber-hot
Text: #000 (black on amber)
Font: Bold
Border-radius: 2px

Hover:
  Background shifts brighter
  Border-bottom: 3px solid #FFF (intense glow)

Pressed:
  Background: linear-gradient(top→bottom)
    0%: #8A7040 (gray-amber, desaturated)
    85%: --amber-muted (#AA8844)
    100%: #887044 (muted bottom)
  Border-bottom: 1px solid #886633 (glow dims)
  Text: #222 (slightly faded)
```

#### Destructive/Discard Buttons
```
Background: transparent
Border: 1px solid transparent
Text: --text-dim (#555)

Hover:
  Border: 1px solid --border (#222)
  Text: --text-muted (#888)
---

### 4.4 Category Buttons (Deck Buttons)

#### Overall Feel
**Rubber mixer switches** — like pressing a button on a physical mixing console. Backlit feel when active.

QSS Selector: `QPushButton#CategoryPill`

```
Default:
  Background: linear-gradient(top→bottom) — backlit technique
    0%: #111111
    85%: #1A1A1A  
    100%: #252525 (lighter at bottom)
  Border: 1px solid --border (#222)
  Border-bottom: 2px solid --border-hover (#333)
  Border-radius: 2px
  Text: --text-muted (#888)
  Font: 11pt, Bold, Uppercase
  Padding: 10px 24px
  Min-width: 100px

Hover:
  Border-bottom: 2px solid --amber
  Text: --text-normal

Active/Checked:
  Background: --void (#050505) with subtle amber tint
  Border-bottom: 3px solid [semantic-color] (Music=blue, Jingle=magenta, etc.)
  Text: [semantic-color]
  — Feels "pressed in" with amber glow bleeding through
```

---

### 4.5 Tag Pills (Filter Tags)

#### Overall Feel
**Removable data tags** — used in Filter Sidebar and Editor. Color-coded, pressable, dismissible.
All tag pills should look consistent regardless of location.

QSS Selector: `QPushButton#NeonChip`

```
Container:
  Background: --chassis (#111)
  Border: 1px solid --border (#222)
  Border-radius: 12px (rounded pill shape)
  Border-bottom: 3px solid [semantic-color]
  Padding: 4px 12px 4px 16px
  Text: --text-normal (#E0E0E0)
  Font: 11pt, Bold

Close button (×):
  Color: --text-dim
  Hover: --text-bright

Hover:
  Border-color: --amber
  Text: --text-bright

Pressed/Removing:
  Background dims briefly before removal
```

---

### 4.6 Input Fields

#### Overall Feel
**Recessed data terminals** — look like they're carved into the console.

```
Default:
  Background: --void (#050505)
  Border: 1px solid --border (#222)
  Border-top: 1px solid #000 (inset shadow effect)
  Border-left: 1px solid #000
  Border-right: 1px solid --border
  Border-bottom: 1px solid --border-hover (#333) (subtle light edge)
  Text: --text-normal (#E0E0E0)
  Font: Consolas, 11pt
  Padding: 6px 8px

Focus:
  Border: 1px solid --amber (#FFC66D)
  Background: #080808
  Text: --text-bright

Invalid:
  Border: 1px solid #FF5252
  Text: #FF5252
```

---

### 4.7 Playback Deck (Bottom Panel)

#### Overall Feel
**The control surface** — elevated, important, distinct from the rest.

```
Container:
  Background: linear-gradient(top→bottom)
    0%: --void (#050505)
    100%: #080808
  Border-top: 1px solid --magenta (#D81B60) (neon rail)
```

#### Transport Buttons (Play/Stop/Skip)
```
Background: linear-gradient (backlit, same technique as buttons)
Border: 1px solid --border
Border-bottom: 2px solid --magenta (playback = magenta)
Text: --text-muted

Hover:
  Border-bottom: 2px solid --magenta-hot
  Text: --text-bright

Big Play Button:
  Background: --magenta
  Border-bottom: 3px solid --magenta-hot
  Text: white
  Font: 14pt Bold
```

#### Waveform/Meter
```
Background: --void
Border: 1px solid --chassis
Gradient fill (left→right):
  0%: #1B5E20 (green)
  60%: #2E7D32
  80%: #FBC02D (yellow warning)
  100%: #B71C1C (red danger)
```

---

### 4.8 Side Panel (Metadata Editor)

#### Overall Feel
**Surgical station** — stacked instrument blades.

```
Container:
  Background: --void (#050505)
  Border-left: 1px solid --rail (#1A1A1A)
```

#### Panel Header
```
Font: 14pt, Bold
Text: --text-bright
Border-bottom: 2px solid --border (or --amber for emphasis)
Padding-bottom: 4px
```

#### Section Headers (e.g., "CORE METADATA")
```
Text: --amber (#FFC66D) ← THIS IS THE GLOWUP CHANGE (was blue)
Font: 11pt, Bold
Border-bottom: 1px solid --border-hover
Margin-top: 12px
```

#### Field Labels
```
QSS Selector: QLabel[objectName="FieldLabel"]
Text: --amber (#FFC66D) — Amber for emphasis, matches section headers
Font: 8pt, Bold, Uppercase
Letter-spacing: 1px
```

---

## 5. EMPTY & LOADING STATES

### 5.1 Empty Panel (No Selection)
Instead of a black void, show:
- Faint Gosling logo (watermark, 10% opacity)
- Text: "SELECT A TRACK" in --text-dim
- Centered, not aggressive

### 5.2 Loading State
- Subtle pulsing animation on amber elements
- Text: "LOADING..." if needed

---

## 6. IMPLEMENTATION PRIORITY

### Phase 1: Color Foundation
1. Fix duplicate QLabel definitions in theme.qss
2. Implement sidebar label contrast fix
3. Unify button colors (amber primary, remove random greens/pinks from non-playback)

### Phase 2: Depth & Glow
1. Apply "backlit button" gradient to all primary buttons
2. Implement amber LED indicators on tree checkboxes
3. Add signal rail selection to table rows

### Phase 3: Polish
1. Zebra striping (make more visible)
2. Empty state for side panel
3. Column header text clipping fix

### Phase 4: Playback Deck
1. Apply magenta-specific treatment to transport controls
2. Ensure visual separation from editor panel

---

## 7. QSS IMPLEMENTATION NOTES

### Gradient Syntax (Qt)
```css
background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 #111,
    stop:0.85 #1A1A1A,
    stop:1 #252525);
```

### Radial Gradient for LEDs
```css
/* Note: Qt QSS does NOT support transparency in gradients. Use solid colors only. */
background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
    stop:0 #FFF,
    stop:0.2 #FFE0B2, 
    stop:0.7 #FFC66D, 
    stop:1.0 #452600);
```

### Inset Effect (Fake)
Use border colors: darker top/left, lighter bottom/right.
```css
border-top: 1px solid #000;
border-left: 1px solid #000;
border-right: 1px solid #222;
border-bottom: 1px solid #333;
```

### Scrollbars
Vertical scrollbars are styled. If horizontal scrollbars appear, apply the same style:
- Border-radius: 6px (more rounded, like a machined cylinder)
- Gradient shading for 3D effect
- No arrow buttons (height/width: 0px)

---

## 8. REFERENCE IMAGES

### 8.1 Concept V1 (Aspirational — Has Non-QSS Elements)
**Path**: `resources/mock/gosling_ui_concept_v1_1766852879603.png`

This mockup includes metal textures, screws, and heavy skeuomorphic details that **cannot be replicated in QSS**. Use for:
- Overall color palette reference
- General "industrial hardware" vibe
- Depth and lighting direction inspiration

**Ignore**: Physical textures, screw details, realistic shadows.

### 8.2 Concept V2 (Target — QSS-Achievable)
**Path**: `resources/mock/gosling_ui_concept_v2_1766853014179.png`

This mockup uses only flat colors, gradients, and glow effects — **everything is achievable in QSS**. This is the primary implementation target.

**Key techniques visible**:
- Backlit button gradients (light from below)
- Amber LED indicators with radial glow
- Signal rail selection (3px left border)
- Inset input fields (darker top/left borders)

---

## 9. KNOWN LIMITATIONS

### 9.1 Requires Python Code (Not QSS)
- **Table row signal rail**: `QTableView::item:selected` can't have left-only border in QSS. Requires custom `QStyledItemDelegate`.
- **Empty state ghost logo**: Requires Python overlay widget or custom painting.

### 9.2 Qt QSS Doesn't Support
- **Transparent gradient stops**: `#FFC66D40` won't work. Use solid colors only.
- **Box shadows**: CSS `box-shadow` has no Qt equivalent. Fake with borders.
- **Blur effects**: No `backdrop-filter`. Not achievable.

---

*This document is a living spec. If something looks bad in practice, throw it away and follow a better lead.*
