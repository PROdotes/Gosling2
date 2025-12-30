# GOSLING2 PANEL STRUCTURE
**The Canvas Before The Paint**

## The Hierarchy

```
Main Window (#050505 - The Chassis/Void)
│
├── 1. TOP BAR (#0A0A0A)
│   ├── App title "GOSLING // WORKSTATION"
│   ├── Category Pills (ALL, MUS, JIN, etc.)
│   └── Border-bottom: 1px solid #222
│
├── 2. LEFT SIDEBAR (#0A0A0A)
│   ├── Command Rail (ALL+, ALL-, MATCH)
│   ├── Filter Tree
│   ├── Chip Bay (#050505 - recessed panel)
│   └── Border-right: 1px solid #222
│
├── 3. CENTER TABLE (#0A0A0A)
│   ├── Column Headers
│   ├── Data Rows (zebra striped)
│   └── No borders (fills remaining space)
│
├── 4. RIGHT EDITOR (#050505 - darker, "surgical panel")
│   ├── Panel header
│   ├── Form sections
│   ├── Action buttons
│   ├── **NO Transport Controls** (Strictly Metadata/History)
│   └── Border-left: 1px solid #1A1A1A
│
└── 5. BOTTOM PLAYBACK DECK (#050505 - distinct)
    ├── Transport controls
    ├── Waveform/progress
    └── Border-top: 1px solid #D81B60 (magenta rail)
```

## The Material Stack

| Surface | Color | Purpose |
|---------|-------|---------|
| Main Window | `#050505` | The deepest void - chassis background |
| Standard Panels | `#0A0A0A` | Top bar, sidebar, table - the working surfaces |
| Recessed Panels | `#050505` | Editor, playback, chip bay - inset/special areas |
| Panel Borders | `#222222` | Visible separation between panels |
| Accent Borders | `#1A1A1A` | Subtle separation (editor) |
| Signal Border | `#D81B60` | Playback deck only |

## Implementation Order

1. **Main window background** → `#050505`
2. **Panel backgrounds** → Top bar, sidebar, table = `#0A0A0A`
3. **Panel borders** → Visible lines creating structure
4. **Recessed panels** → Editor, playback, chip bay = `#050505`
5. **Then and only then** → Style individual elements

## Why This Matters

Without this foundation:
- Elements have no context (chips floating in void)
- No visual hierarchy (everything blends together)
- Changes break the design (no stable reference)

With this foundation:
- Elements are "mounted" on surfaces
- Clear visual structure (panels are distinct)
- Design is resilient (elements relate to their panel, not arbitrary colors)
