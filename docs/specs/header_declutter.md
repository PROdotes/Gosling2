# Header declutter + Settings home

Status: DEFERRED (2026-06-17). Owner parked the declutter pending a future
full redesign. One decision locked: **Filter toggle stays in the global header
(option a)** — never move it into the reflowing song list (see step 1). The
rest of this plan is preserved for when the redesign is picked up.

## Problem

The top `<header>` is a single 52px flex row (`base.css:133`) packing four
zones into one strip:

1. `GOSLING.` logo (`.header-logo`)
2. Mode nav — **7** tabs: Songs, Albums, Artists, Publishers, Tags, Ingest, Log
3. Search cluster — search input + Deep toggle + `Filter ▼` button
4. Stats bar — one stat (`margin-left:auto`)

No `@media` rules on the header → it never reflows, just tightens. Settings
(API wired: `GET/POST /api/v1/settings`) has nowhere clean to go.

## Hard layout constraint (why a left nav rail is rejected)

Horizontal edges are already owned by per-mode workspace chrome:

- **Songs** (`#songs-workspace`): `filter-sidebar | song-list | editor +
  action-sidebar` — **both** the far-left (filters) and far-right (song-edit
  action buttons) are occupied. This is the tightest mode.
- **Entity** (Albums/Artists/Publishers/Tags): `entity-list-pane |
  entity-detail-pane`.
- **Ingest / Log**: single container.

A global left nav rail (the earlier Option A) would add a 4th left-edge band
precisely where Songs has the least room. **Rejected.**

Conclusion: the **top bar is the correct home for global controls** *because*
the edges belong to per-mode chrome. The fix is to thin the bar's contents, not
move them sideways.

## What is actually global vs contextual (verified)

- **Search input + Deep toggle = global.** One `#searchInput` drives all modes;
  `switchMode` only swaps its placeholder (`main.js:482`) and Deep is search
  behavior (`main.js:1301`). Stays in the header.
- **`Filter ▼` = Songs-only, misplaced.** `toggle-filter-sidebar` →
  `filterSidebar.toggle()` (`main.js:1260`); the filter sidebar lives only in
  `#songs-workspace`. A mode-specific control sitting in the global strip.
- **Stats bar = contextual.** It counts the active mode's list.
- **Mode nav = global** but mixes two kinds: entity browsers (Songs/Albums/
  Artists/Publishers/Tags) vs utilities (Ingest, Log).

Existing seam to exploit: **each workspace already has its own header** — the
song list has `.list-header` (holds the sort `<select>`), entities have
`.entity-list-header` with an empty `#entity-list-actions` slot. Contextual
controls can move into these without inventing a new global row.

## Mechanism (what's safe to move)

Mode switching is fully delegated: tabs work by `data-action="switch-mode" +
data-mode`, dispatched in `handlers/navigation.js`; `syncModeUi()` finds them by
`.mode-tab`. So tab DOM position is free to change with **no JS rewrite**, as
long as the three hooks (`.mode-tab`, `data-action`, `data-mode`) are kept.
Ingest's badge + drop-zone wiring selects by `data-mode='ingest'`, so it follows
the element.

## Revised plan: thin the top bar (formerly Option B, now grounded)

1. **Filter toggle — DO NOT move it into a reflowing element.** The filter
   sidebar is in normal flex flow (`width:220px`, `.hidden`→`width:0`), so it
   *pushes* the song list. A toggle placed in `.list-header` shifts right by
   220px when the sidebar opens → the button walks out from under the cursor
   (tried before; rejected). **Invariant:** the toggle must sit at an x that is
   constant across the toggle. Two acceptable homes:
   - (a) **Leave it in the global header** (current, stationary). Zero risk; it
     stays a global-bar resident and the decluttering comes from steps 2-4.
   - (b) **A persistent thin filter gutter pinned at the workspace left edge
     (x=0).** The 220px panel expands *rightward* from the gutter; the toggle
     handle never moves while the list reflows beside it. Colocates the control
     with the filter and keeps the global bar clean, at the cost of
     restructuring the sidebar into rail + panel. Owner picks (a) or (b).
2. **Relocate the stat count into the per-mode list header.** Songs →
   `.list-header`; entities → `#entity-list-actions`. Frees the right end of the
   header. (Keep the `id`s — `match-count`/`total-count`/`total-label` are read
   in `main.js`; move the nodes, don't rename.)
3. **Regroup mode nav** into two visual groups in the header: entity browsers as
   a segmented control, Ingest + Log as a small trailing utility pair (they are
   workflow/debug, not browsers).
4. **Settings = right-side gear → modal.** Add a gear to a small
   `.header-utility` cluster on the right (where stats used to anchor). Opens a
   tabbed modal (reuse `modals.css`): General now, Renaming Rules later
   (backlog gap #2). Fed by `GET/POST /api/v1/settings`; a `settings_load`
   warning renders as an in-modal banner.

Net header after: logo | [entity tabs] [Ingest｜Log] | search + Deep | gear.
Filters and counts live with the content they describe.

## Alternatives still on the table

- **Two-tier top region:** keep row 1 global (logo, nav, search, gear); add a
  thin row 2 contextual toolbar per mode. Cleanest separation but +~40px
  vertical and partly duplicates the per-mode headers that already exist —
  hence the revised plan prefers reusing those existing headers over a new row.
- **Minimal:** only add the Settings gear, leave everything else. Unblocks
  Settings but does not address crowding.

## Open questions for owner

1. Go with the revised "thin the top bar" plan, the two-tier variant, or
   minimal?
2. Filter toggle: (a) leave it in the global header (stationary, zero risk) or
   (b) build a persistent left-edge filter gutter so it colocates with the
   filter without moving on toggle?
3. Move the stat count into the per-mode list headers, or leave it in the
   global bar for now (smaller change)?
4. Ingest + Log: keep as visible trailing tabs, or demote Log into a utility/
   overflow (it is a debug view)?
5. Settings as a tabbed modal — confirm vs. a dedicated full screen?
