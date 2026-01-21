
# T-Tools: Global Entity Management & Library Maintenance

## 1. The Problem Definition: "Solo Pilot" vs. "Flight Crew"

The application currently suffers from **"Context Blindness."** All metadata management is tied to a specific song selection. This creates a friction trap:

*   **The Orphan Ghost**: If a user creates a typo tag (e.g., "Rockk") and fixes it on all songs, that tag remains a "ghost" in the database. Without a song linked to it, the tag becomes invisible and un-deletable through the current UI.
*   **The Jazler Friction**: In traditional broadcast software, "Maintenance" is often a separate application or mode. For a **"Solo Pilot"** (one person DJing and editing), exiting the live deck to fix a typo in a manager is high-friction.
*   **The Big Radio Conflict**: A **"Big Radio"** DJ doesn't want their UI cluttered with maintenance tools. The challenge is providing **"Stealth Power"**—tools that are invisible during normal operation but instant during maintenance.
*   **Architectural Debt**: The `SidePanelWidget` is a 2,700-line monolith. It conflates song-editing with entity-management, making the UI fragile and hard to extend with global tools.

---

## 2. Objective
Establish a system for managing Artists, Albums, and Tags independent of song context, allowing for "Live Data Healing" without disrupting the broadcast flow.

---

## 3. Design Concepts for Consideration

### Concept A: The "Workstation Deck" (UI Swapping)
Refactor the Right Panel (Side Panel) into a **Stateful Deck**. 
*   **Behavior**: Instead of just saying "No Selection," the panel pivots between **[Song Editor]** (when tracks are selected) and **[Global Inventory]** (when selection is cleared or tool is toggled).
*   **Pros**: Zero new UI real estate needed. Solves the "Blank Screen" bug.
*   **Cons**: May be "too clever" if a user wants to manage tags while a song is selected.

### Concept B: The "Edit-on-Sight" Search Integration
Embed management actions directly into the **Global Search Results**.
*   **Behavior**: Searching for "Pink Floid" returns the artist record. A small icon (wrench or red-dot) appears next to the record. Clicking it opens a standalone manager instance in the side panel.
*   **Pros**: Lowest friction. No "navigation" required.
*   **Cons**: Search results could become cluttered with "action noise."

### Concept C: The "Library Health" Fallback
Transform the "No Selection" state of the workstation into a proactive **Maintenance Dashboard**.
*   **Behavior**: When no songs are clicked, the panel shows:
    - `[ 🏷️ 3 Orphan Tags Found ]`
    - `[ 🎭 1 Empty Artist Found ]`
    - `[ 💿 5 Duplicate ISRCs ]`
*   **Pros**: Encourages regular maintenance. Turn "Zero State" into "Value State."
*   **Cons**: Requires a background "Health Check" service to avoid UI lag.

### Concept D: The "Tools Ribbon" (Explicit Management)
Add a "Tools" dropdown or secondary toggle to the **Right Panel Header**.
*   **Behavior**: Next to `[EDIT MODE]`, add a `[ TOOLS ]` button. This opens a modal or a slide-out overlay dedicated to the **"Master Inventory"** (filtering, nuking, merging).
*   **Pros**: Very clear mental model. Delineates "Maintenance Session" from "Quick Fix."
*   **Cons**: Adds a new visual element to a high-density area.

---

## 4. Technical Requirements (The "How")
1.  **Extract Entity Logic**: Move all `Delete`, `Merge`, and `Cleanup` logic out of UI widgets and into a dedicated `InventoryService`.
2.  **Usage Counts**: Repositories must support `GET COUNT(usage)` to allow for "Delete if Usage == 0" logic.
3.  **Destructive Modes**: Distinguish between **"Unlink"** (Song Context) and **"Nuke"** (Global Context) via a shared `EntityClickRouter`.
4.  **Refactor SidePanelWidget**: Break the 2,700-line file into a component-based "Field Registry" where the same Tag Chip logic is shared between the Song Editor and Global Manager.

---

## 5. Interaction Mandates
- **No interactive popups** for simple deletions of 0-usage entities.
- **Fail-safe confirmation** for entities with >0 usage.
- **Strictly Industrial Amber aesthetics**: Use the hardware-console look (Glow buttons, inset wells).

---

## 6. CHOSEN SOLUTION: Floating Tools Window (QMainWindow)

After analysis, the chosen approach is a **hybrid of Concepts C + D** implemented as an **independent floating window**.

### 6.1 Core Principle: Two Complementary Workflows

| Workflow | Entry Point | Mental Model |
|----------|-------------|--------------|
| **Context-Specific** | Side Panel → Entity chip → Existing Managers | "Fix this song's album" |
| **Global Maintenance** | Tools Window (Ctrl+T or Menu) | "Clean up all orphan tags" |

The Tools Window **does not replace** existing dialogs (`AlbumManagerDialog`, `ArtistDetailsDialog`, `PublisherDetailsDialog`). It complements them for bulk/global operations.

### 6.2 Access Points
- **Keyboard**: `Ctrl+T` (global shortcut)
- **Menu**: Logo dropdown → "🔧 LIBRARY TOOLS"

### 6.3 Window Behavior
- **QMainWindow** (independent, can minimize to taskbar)
- **Non-modal** (main window stays interactive)
- **Resizable**, remembers geometry between sessions
- **Single instance** (re-focuses if already open)

### 6.4 UI Layout

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  🔧 LIBRARY TOOLS                                                 [_][□][X]  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ [ 🏷️ Tags ] [ 🎭 Artists ] [ 💿 Albums ] [ 🏢 Publishers ] [ ⚠️ Health ]      ║
╠═══════════════════════════════════════════════╦══════════════════════════════╣
║ 🔍 Filter: [_______________]  [☑ Orphans Only] ║                              ║
╠═══════════════════════════════════════════════╣      I N S P E C T O R       ║
║ NAME              │ USAGE │ ACTIONS            ║                              ║
║───────────────────┼───────┼────────────────────║  Name: [Rock_____________]   ║
║ Rock              │  47   │ [Merge▾] [🗑️]      ║                              ║
║ Rockk (typo!)     │   0   │ [Merge▾] [🗑️]  ←── ║  Usage: 47 songs             ║
║ Jazz              │  12   │ [Merge▾] [🗑️]      ║                              ║
║ ...               │       │                    ║  [ SAVE ]                    ║
╚═══════════════════════════════════════════════╩══════════════════════════════╝
```

### 6.5 Tab Specifications

#### 🏷️ Tags Tab
- **List columns**: Name, Usage Count, Actions
- **Inspector**: Tag name (editable), usage stats
- **Actions**: Rename, Merge (dropdown of targets), Delete
- **Filter**: Text search, "Show Orphans Only" toggle

#### 🎭 Artists Tab
- **List columns**: Name, Type (Person/Group), Song Count, Actions
- **Inspector**: Name, Sort Name, Type toggle, Aliases (EntityListWidget), Members (EntityListWidget)
- **Actions**: Rename, Merge, Delete
- **Filter**: Text search, Type filter, "Show Orphans Only" toggle

#### 💿 Albums Tab
- **List columns**: Title, Artist, Year, Song Count, Actions
- **Inspector**: Title, Album Artist (EntityListWidget), Year, Type, Publisher (EntityListWidget)
- **Actions**: Edit, Merge, Delete
- **Filter**: Text search, Year range, "Show Orphans Only" toggle

#### 🏢 Publishers Tab
- **List columns**: Name, Parent, Song Count, Actions
- **Inspector**: Name, Parent selector, Children (EntityListWidget)
- **Actions**: Rename, Merge, Delete
- **Filter**: Text search, "Show Orphans Only" toggle

#### ⚠️ Health Tab
- **Summary Dashboard**:
  ```
  🏷️  3 Orphan Tags        [ SHOW ] [ NUKE ALL ]
  🎭  1 Empty Artist       [ SHOW ] [ NUKE ALL ]
  💿  0 Empty Albums       ✓ Clean
  🏢  2 Orphan Publishers  [ SHOW ] [ NUKE ALL ]
  🔀  5 Duplicate ISRCs    [ REVIEW ]
  ```
- "SHOW" switches to the relevant tab with orphan filter active
- "NUKE ALL" deletes all 0-usage entities (no confirmation for orphans)

---

## 7. Implementation Plan

### 7.1 New Files
| File | Purpose |
|------|---------|
| `src/presentation/windows/tools_window.py` | Main QMainWindow class |
| `src/presentation/widgets/tools_tab_base.py` | Base class for entity tabs |
| `src/presentation/widgets/tools_tag_tab.py` | Tags management tab |
| `src/presentation/widgets/tools_artist_tab.py` | Artists management tab |
| `src/presentation/widgets/tools_album_tab.py` | Albums management tab |
| `src/presentation/widgets/tools_publisher_tab.py` | Publishers management tab |
| `src/presentation/widgets/tools_health_tab.py` | Health dashboard tab |
| `src/business/services/inventory_service.py` | Centralized entity management logic |

### 7.2 Modified Files
| File | Changes |
|------|---------|
| `custom_title_bar.py` | Add "🔧 LIBRARY TOOLS" to logo dropdown menu |
| `main_window.py` | Add `Ctrl+T` shortcut, instantiate/manage Tools window |
| `tag_repository.py` | Add `get_usage_count()`, `get_all_with_usage()` |
| `contributor_repository.py` | Add `get_usage_count()`, `get_all_with_usage()` |
| `album_repository.py` | Add `get_usage_count()`, `get_all_with_usage()` |
| `publisher_repository.py` | Add `get_usage_count()`, `get_all_with_usage()` |

### 7.3 Phased Delivery
1. **Phase 1 (MVP)**: Tags tab + Health tab (addresses "Orphan Ghost" problem)
2. **Phase 2**: Artists tab + Publishers tab
3. **Phase 3**: Albums tab (may share code with existing AlbumManagerDialog)

---

## 8. Open Questions
- [ ] Should merging open a confirmation showing affected songs?
- [ ] Should "Nuke All Orphans" have a final confirmation, or truly be instant?
- [ ] Should the Tools window remember which tab was last active?

