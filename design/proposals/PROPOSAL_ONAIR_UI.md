# On-Air UI Proposal

**GitHub Issue:** Part of #7  
**Status:** 🔮 Future (after Broadcast Automation)  
**Depends On:** Timeslots, ContentRules, PlaybackService refactor

---

## Overview

A simplified, high-contrast interface for the broadcast studio. Optimized for live radio operation with touchscreen support.

---

## Phase 5.1: Live Assist View

The primary on-air screen for human-driven broadcasting.

### Triple Stack Display
Visual representation of the current and upcoming items:
```
┌─────────────────────────────────────┐
│  NOW PLAYING                        │
│  ▶ "Hey Jude" - The Beatles         │
│  [=========----] 2:34 / 4:02        │
├─────────────────────────────────────┤
│  NEXT                               │
│  "Let It Be" - The Beatles          │
├─────────────────────────────────────┤
│  NEXT +1                            │
│  Station Jingle                     │
└─────────────────────────────────────┘
```

### Big Control Buttons
Massive, touchscreen-friendly controls:
- **▶ START** — Green, starts next item
- **⏹ STOP** — Red, hard stop
- **⏭ NEXT** — Skip to next item (with optional crossfade)
- **🔇 FADE** — Gradual fade out

### Clocks & Timers
- **Song Countdown** — Time remaining on current track
- **Segue Timer** — Time until crossfade point
- **Hard Event Clock** — Countdown to scheduled events (News at :00, etc.)

---

## Phase 5.2: Cart Wall

Grid of instant-play buttons for sound effects, beds, and drops.

```
┌────┬────┬────┬────┐
│ 🔊 │ 📣 │ 🎺 │ 🥁 │
│ SFX│Drop│Horn│Drum│
├────┼────┼────┼────┤
│ 🎵 │ 🎶 │ 🔔 │ ⏰ │
│Bed1│Bed2│Bell│Time│
└────┴────┴────┴────┘
```

- **Drag & Drop** — Load sounds onto buttons
- **Color Coding** — Different colors for SFX, beds, jingles
- **Ducking** — Option to auto-duck main audio when cart plays

---

## UI Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Manual** | Simple player (current state) | Testing, casual listening |
| **Live Assist** | Stops at break points, human triggers next | Live shows |
| **Full Automation** | System picks songs from Timeslots | Overnight, unmanned |

---

## Open Questions

1. **Keyboard Shortcuts** — F-keys for cart buttons?
2. **Remote Control** — Mobile app to trigger events?
3. **Multiscreen** — Separate display for cart wall?

---

*Last updated: Dec 18, 2024*
