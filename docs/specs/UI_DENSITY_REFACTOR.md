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

## CSS Logic (Draft)
```css
#results-container {
    gap: 0;
    padding: 0;
}

.result-card {
    border: none;
    border-bottom: 1px solid var(--border-subtle);
    border-radius: 0;
    padding: 0.6rem 1rem;
    gap: 0.8rem;
    align-items: center;
    background: transparent;
}

.result-card.active {
    border: none;
    border-bottom: 1px solid var(--border-subtle);
    border-left: 4px solid var(--accent);
    background: linear-gradient(90deg, rgba(249, 115, 22, 0.12), transparent);
}

.card-icon {
    width: 32px;
    height: 32px;
    font-size: 0.9rem;
    border-radius: 8px;
}

.card-subtitle {
    margin-top: 0.15rem;
    font-size: 0.8rem;
}

.card-meta {
    margin-top: 0.4rem;
    gap: 0.35rem;
}

.pill {
    padding: 0.12rem 0.45rem;
    font-size: 0.7rem;
}
```

## Verification Plan
1. **Visual Regression**: Compare before/after screenshots.
2. **Scroll Test**: Ensure 36 songs feel manageable.
3. **Interactive Elements**: Verify selection and toggle switches.
