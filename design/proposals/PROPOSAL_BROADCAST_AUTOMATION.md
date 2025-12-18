# Broadcast Automation Proposal

**GitHub Issue:** #7  
**Status:** 📋 Planned (Far Future)  
**Depends On:** PlayHistory, Log Core, Field Registry

---

## Overview

Automated scheduling system for radio programming. Defines time-based "slots" with content rules that the system uses to auto-generate playlists.

---

## Database Schema

### `Timeslots` (was AutomationPhases)
Time-based blocks for scheduling. Covers 0-24 hours; unfilled times use the Default slot.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `TimeslotID` | INTEGER | PRIMARY KEY | Unique identifier |
| `Name` | TEXT | NOT NULL UNIQUE | "Default", "Morning Drive", "Jazz Hour" |
| `StartTime` | TEXT | NOT NULL | "06:00", "22:30" (HH:MM format) |
| `EndTime` | TEXT | NOT NULL | "10:00", "23:00" |
| `DaysOfWeek` | TEXT | - | JSON: `["Mon","Tue"]` or NULL for all |
| `Priority` | INTEGER | DEFAULT 0 | Higher priority wins on overlap |
| `IsDefault` | BOOLEAN | DEFAULT 0 | Fallback slot |

### `ContentRules` (was PhaseRules)
Content sequence within each slot. Defines what plays and in what order.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `RuleID` | INTEGER | PRIMARY KEY | Unique identifier |
| `TimeslotID` | INTEGER | FK NOT NULL | Reference to `Timeslots` |
| `Position` | INTEGER | NOT NULL | Order (0, 1, 2...) |
| `ContentType` | TEXT | NOT NULL | 'Song', 'Jingle', 'Commercial', 'Any' |
| `Filters` | TEXT | - | JSON filter criteria |
| `LoopTo` | INTEGER | - | Position to loop back to |

---

## Interference Detection

> [!CAUTION]
> **Critical Requirement:** The system MUST detect conflicts that would result in 0 playable songs.

### Conflict Scenarios

1. **Additive Conflict:**  
   User adds a "Jazz Hour" slot (22:00-23:00) with rule `{"genre": "Jazz"}`.  
   A global rule exists: `{"exclude_mood": "Slow"}`.  
   If all Jazz songs in the library are tagged as Slow → **0 songs can play**.

2. **Subtractive Conflict:**  
   User adds global rule `{"exclude_mood": "Slow"}`.  
   An existing "Late Night" slot has rule `{"genre": "Ambient"}`.  
   If all Ambient songs are Slow → **Late Night has 0 songs**.

### Detection Algorithm

Before saving any Slot or Rule:
```
1. For each Timeslot:
   2. Collect all applicable rules (slot rules + global rules)
   3. Build combined filter query
   4. COUNT songs matching the filter
   5. If count == 0:
      - WARN: "Timeslot '{name}' has 0 matching songs with current rules"
      - Show which filters are causing the conflict
      - Allow save anyway (with warning logged)
```

### UI Feedback

- **Yellow Warning:** "This rule reduces Jazz Hour to 3 songs"
- **Red Error:** "This rule would leave Jazz Hour with 0 songs"
- **Dry Run:** Preview button shows what songs match before saving

---

## Sequence Logic

### Example: "Jazz Hour" (22:00-23:00)

| Position | ContentType | Filters | LoopTo |
|----------|-------------|---------|--------|
| 0 | Jingle | {} | - |
| 1 | Song | {"genre": "Jazz", "mood": "Mellow"} | - |
| 2 | Song | {"genre": "Jazz", "mood": "Upbeat"} | - |
| 3 | Song | {"genre": "Jazz"} | 1 |

**Execution:** Jingle → Mellow Jazz → Upbeat Jazz → Any Jazz → (loop to pos 1)

### Example: "Pop Hits Hour" (no breaks)

| Position | ContentType | Filters | LoopTo |
|----------|-------------|---------|--------|
| 0 | Song | {"genre": "Pop", "year": 2024} | 0 |

**Execution:** Just plays current-year Pop on repeat.

---

## Open Questions

1. **Global Rules:** Should there be a "Global Rules" slot that applies to ALL timeslots?
2. **Exclusions:** Support `exclude_*` filters? e.g., `{"exclude_artist": "Nickelback"}`
3. **Weights:** Should some songs be preferred? e.g., "Play hits more often"
4. **Artist Separation:** "Don't repeat same artist within 60 minutes" — where does this go?

---

## Implementation Phases

1. **Schema Only** — Add tables, no logic
2. **Static Rules** — Manual slot creation, no interference detection
3. **Interference Detection** — Validation before save
4. **Auto-Scheduler** — Generate playlists from slots
5. **UI Editor** — Visual slot/rule editor

---

*Last updated: Dec 18, 2024*
