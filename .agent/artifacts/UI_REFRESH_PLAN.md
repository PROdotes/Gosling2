# UI Refresh Plan - Visual Consistency Pass

## Goal
Match the polished "Pro Audio Console" aesthetic established in:
- Side Panel Editor (labels, chips, chip trays, inputs)
- Title Bar (amber accent, raised buttons)

## Design Language Reference
```
COLORS:
- Amber Accent: #FFC66D
- Warm Amber Labels: #9A8A70 (subtle guides)
- Data Text: #E0E0E0 (bright, readable)
- Dim Text: #888888 (secondary)
- Very Dim: #555555 (disabled/managed)
- Panel BG: gradient #2A2A2A -> #080808
- Inset Wells: #000000 -> #0A0A0A -> #151515
- Raised Elements: #555555 -> #3D3D3D -> #2D2D2D -> #1A1A1A

SPACING:
- Glow margin: 5px
- Border radius: 8-10px
- Content padding: 8px typical

BORDERS:
- Raised: 1px solid #000000 (dark outline)
- Inset Top/Left: #222222 (shadow)
- Inset Bottom/Right: #444444 (highlight)
```

---

## Phase 1: Filter Panel (Left Side)

### Current State:
- Basic tree view with text items
- LED indicators next to some items
- Flat appearance

### Changes Needed:

**1.1 Section Headers (Active, Album, Artist, Status, etc.)**
- Apply warm amber color (#9A8A70) 
- Uppercase, letter-spacing: 1.5px
- font-size: 10pt, font-weight: bold
- Target: `#FilterTree` branch items at depth 0

**1.2 Tree Items (leaf nodes)**
- Default: #888888 text
- Hover: #FFFFFF text + subtle background (#1A1A1A)
- Selected: Amber signal rail (3px left border #FFC66D) + #222222 bg

**1.3 LED Indicators**
- Already styled - verify they match

**1.4 Overall Panel**
- Should inherit the panel gradient already

---

## Phase 2: Library Table (Center)

### Current State:
- Headers are amber - GOOD
- Row text is dim gray
- No visible selection styling
- Low contrast

### Changes Needed:

**2.1 Table Headers**
- ✓ Already amber (#FFC66D) - keep
- Add slight bottom border for definition
- Consider warm amber (#9A8A70) instead for consistency with labels

**2.2 Row Styling**
- Default text: #CCCCCC (brighter than current #888888)
- Alternate row: #111111 (subtle stripe) 
- Hover: gradient bg like raised button, text #FFFFFF
- Selected: 3px left amber border + #1A1A1A bg + #E0E0E0 text

**2.3 Row Height**
- min-height: 32px for comfortable reading

---

## Phase 3: Playback Deck (Bottom)

### Current State:
- Buttons look reasonably polished (raised style)
- X-FADE combo has corner notch - GOOD
- Progress bar is basic
- Transport buttons could be more prominent

### Changes Needed:

**3.1 Progress Bar**
- Track: Inset gradient like input wells
- Handle: Raised button gradient
- Fill: Amber (#FFC66D) gradient

**3.2 Transport Buttons (PLAY, PAUSE, STOP)**
- Already styled - verify consistency
- PLAY could have amber glow when active

**3.3 Time Display**
- Monospace font (Consolas)
- Amber text (#FFC66D)
- Inset background

---

## Phase 4: Category Pills (Top Row)

### Current State:
- ALL, ALL(4), MUS(4), etc.
- Raised button style
- Active has color glow

### Changes Needed:
- Verify consistency with button styles
- Active state should be clear (amber? or category color?)

---

## Phase 5: Active Filter Chip (Bottom Left)

### Current State:
- "tags: Genre:Cro ×" - Amber chip
- Looks decent

### Changes Needed:
- Verify matches the editor chip styling

---

## Implementation Order

1. **Filter Panel Tree** - Highest visual impact
2. **Library Table Rows** - Most used component
3. **Scrollbars** - Often overlooked
4. **Playback Progress Bar** - Polish
5. **Final consistency check** - Category pills, dialogs

---

## QSS Selectors Reference

```css
/* Filter Tree */
#FilterTree { }
#FilterTree::item { }
#FilterTree::item:hover { }
#FilterTree::item:selected { }
#FilterTree::branch { }

/* Library Table */
#LibraryTable { }
#LibraryTable::item { }
#LibraryTable::item:hover { }
#LibraryTable::item:selected { }
#LibraryTable::item:alternate { }
#LibraryHeader::section { }

/* Playback */
QSlider::groove:horizontal { }
QSlider::handle:horizontal { }
QSlider::sub-page:horizontal { }

/* Scrollbars */
QScrollBar:vertical { }
QScrollBar::handle:vertical { }
```
