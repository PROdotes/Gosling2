# Specification: Header Transition (Professional Slim Design)

## Context
The dashboard header currently uses a chunky, rounded design (70px+) that clashes with the high-density workstation (Songs V2) aesthetic. The `edit-design-poc.html` established a 48px slim, industrial design as the target.

## Proposed Changes

### 1. Global Styles (`src/static/css/dashboard/base.css`)
- **Variables**: Initialize `--bg-master` if missing (mapped to `#030407`).
- **Header**: 
    - Set `height: 48px`.
    - Set `padding: 0 16px`.
    - Background: `var(--bg-master)`.
    - Border-bottom: `1px solid var(--border-subtle)`.
- **Logo**: 
    - Drop `.logo` in favor of `.header-logo`.
    - `font-size: 14px`, `font-weight: 700`, `letter-spacing: 1px`.
- **Tabs (`.mode-tabs`)**:
    - Remove background-pill styling.
    - Transparent container, `gap: 8px`.
    - `.mode-tab`: `font-size: 11px`, `font-weight: 700`, `text-transform: uppercase`.
    - Active state: No background change, just `color: var(--text-pure)` and a small underline or glow (from `base.css` accent).
- **Search (`.header-search`)**:
    - Slim input wrapper (`32px` height).
    - Integrated search icon and Deep toggle.

### 2. Dashboard Skeleton (`src/templates/dashboard.html`)
- Re-structure the `<header>` block to match the POC layout.
- Preserve all existing `id`s (`mode-songs`, `searchInput`, `deepSearchToggle`, `match-count`, etc.) for JS compatibility.
- Ensure the `stats-bar` is compact and right-aligned.

## Verification Protocol
1. **Visual**: Header height is exactly 48px. Tabs are slim and uppercase.
2. **Functional**: 
    - Mode switching (clicking tabs) survives the change.
    - Search input remains functional.
    - Deep Search toggle remains functional.
    - Library stats update as expected.
