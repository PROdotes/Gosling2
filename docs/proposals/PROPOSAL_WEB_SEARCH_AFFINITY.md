# PROPOSAL: Web Search Contextual Affinity (T-82)

## 📌 The Problem
Users feel a "disconnect" between empty fields (like Composers) and the "WEB" button at the bottom of the Side Panel. The button lacks contextual "affinity"—it's physically distant from the data it's meant to help find.

## 🎯 Objective
Improve the "scouting" workflow by bringing search triggers closer to the fields that need data.

## 🛠️ Proposed Solutions

### 1. The Split-Search Module
- **Primary Button**: Replaces "WEB" text with a **Magnifying Glass Icon** (Vector). Triggers standard broad search.
- **Menu Button**: A narrow, adjacent button (same height) with a **Down Arrow**.
- **The Gap**: A fixed `5px` margin between them to allow the `GlowButton` halos to breathe and be distinct.
- **Interaction**:
    - Left-Click Main: Performs default search context.
    - Left-Click Arrow: Opens the "Context Menu" (previously Right-Click only), allowing specific searches (Google, MusicBrainz, etc.).

### 2. Field-Level Triggers (The Affinity)
- **Inline Magnifier**: Add a small `magnifying-glass` icon inside or next to the `Composers` line edit when it is empty.
- **Empty State Hint**: Display a ghosted placeholder like `Click SEARCH below to lookup...` when a high-priority field is empty.

### 3. Smart Highlighting & Provider Constraints
- **General Web (Google)**: Construct query `"{Artist} {Title} {FieldName}"`. Effect: Opens Browser.
- **Media (Spotify/YouTube)**: **DISABLE** inline search. These platforms are for playback, not metadata research.
- **Databases (Discogs/MusicBrainz)**: Requires **API Integration**.
  - *Naive*: Search website for `"{Artist} {Title}"` (User must dig for field).
  - *Pro Approach*: Use API to fetch metadata and *propose* the missing value (Auto-Fill).

**Decision**: For V1, Affinity Magnifiers will **only** act safe for Text Search providers (Google). If Discogs/MB is selected, they trigger a general "Release Search" or require the T-90 (API Fetch) module.

## ✅ Implementation Details (Implemented 2025-12-31)

### 1. Split-Search Module
The singular "WEB" button was replaced by a **Split-Button Module**:
- **Action Button (Left)**: Icon `🔍`. Executes the default search. Custom radius (10px Left, 2px Right).
- **Menu Button (Right)**: Icon `▼`. Opens Provider Menu. Custom radius (2px Left, 10px Right).
- **Gap**: Fixed `20px` spacing separates this module from the Workflow Controls (LED + Pending).

### 2. Inline Affinity (Magnifiers)
- **Component**: `GlowLineEdit` now supports `add_inline_tool(icon_normal, callback, tooltip, icon_hover)`.
- **Logic**: Adds a flat `QPushButton` to the right side of the input field (inside the Glow Frame).
- **Visibility**: Automatically hides when field has text. Shows when empty.
- **Glass Glow Effect**:
  - Requires **Two Icons** (Tuple) generated dynamically via `_get_magnifier_icons`.
  - **Normal**: Light Grey (`#CCCCCC`).
  - **Hover**: Amber (`#FFC66D`) with a **Multi-Pass Glow** (Thick semi-transparent underlay + Sharp overlay) drawn via `QPainter`.
  - The Button swaps these icons on `enterEvent`/`leaveEvent`.

### 3. Provider Logic (`_get_search_url`)
- **Google**: Appends Field Name to query (e.g. `Artist Title [Composer]`).
- **Others**: Uses standard `Artist Title` query (safer than bad context).
- **MusicBrainz**: Uses `indexed` release search.

## 📈 Success Criteria
- Boss no longer asks "How do I find the composer?".
- Reduced eyes-off-field movement during the metadata scouting phase.
