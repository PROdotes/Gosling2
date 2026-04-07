# UI Density Refactor: GOSLING2 Sleek List

The current "Bubble Card" layout for song results consumes significant vertical space, limiting visibility to ~4 items on standard resolutions. This spec outlines a transition to a high-density, glass-divider list layout.

## Goals
- Increase item visibility from ~4 songs to ~10-12 songs per screen height.
- Maintain premium "GOSLING" aesthetic (neon accents, glassmorphism, smooth transitions).
- Improve readability of metadata (Title, Artist, Genre) in a compact format.

## Proposed Changes

### 1. Results Container (`#results-container`)
- **Current**: `gap: 0.75rem`, `padding: 1rem`.
- **Target**: `gap: 0`, `padding: 0`. The list will flow as a single contiguous surface.
- **Divider**: Each item will have a bottom border.

### 2. Result Card (`.result-card`)
- **Structure**: Change from a standalone card to a list row.
- **Border/Radius**: 
    - Remove large `border-radius: 14px`.
    - Replace with a `border-bottom: 1px solid var(--border-subtle)`.
    - Remove top/side/right/left borders to create a "flush" list.
- **Padding**: 
    - Reduce from `1rem 1.15rem` to `0.6rem 1rem`.
- **Background**: 
    - Use a subtle glass effect (rgba transparency).
    - **Active State**: Use a left-border glow (`border-left: 3px solid var(--accent)`) and a radiant background.

### 3. Iconic Representation (`.card-icon`)
- **Current**: `42x42px` box with a large glyph.
- **Target**: `32x32px`. Use a more minimal icon.

### 4. Metadata Clusters
- **Subtitle (Artist)**: Reduce top margin from `0.3rem` to `0.15rem`.
- **Meta Row**: Reduce top margin from `0.55rem` to `0.35rem`.
- **Pills**: Shrink pill padding from `0.24rem 0.55rem` to `0.12rem 0.45rem`.
- **Actions (Toggle/ID)**: Vertically center the switch and #ID badge.

## Final Implementation: Horizontal Multi-Column List

The refactor successfully doubled the viewable capacity (from 4.5 to 9 items) by moving from a vertical stack to a horizontal multi-column distribution.

### Final Structure
- **Left Column**: Playback Icon (32x32px).
- **Center-Left Column (Body)**: Title and Subtitle (Artist) stacked vertically.
- **Center-Right Column (Meta)**: Metadata pills (Genre, Year, Duration) right-aligned, capped at 35% width.
- **Far-Right Column (Actions)**: Active toggle switch and #ID badge.

### Visual Tokens
- **Padding**: `0.65rem 1.15rem`.
- **Dividers**: `1px solid var(--border-subtle)` (bottom-only).
- **Active State**: `border-left: 4px solid var(--accent)` + radiant sweep.
