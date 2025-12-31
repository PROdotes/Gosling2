# PROPOSAL: Web Search Contextual Affinity (T-82)

## 📌 The Problem
Users feel a "disconnect" between empty fields (like Composers) and the "WEB" button at the bottom of the Side Panel. The button lacks contextual "affinity"—it's physically distant from the data it's meant to help find.

## 🎯 Objective
Improve the "scouting" workflow by bringing search triggers closer to the fields that need data.

## 🛠️ Proposed Solutions

### 1. Labeling & Phasing
- **Rename Button**: Change `WEB` to `SEARCH 🔍` or `FIND DATA`.
- **Search Pulse**: When the Search button is hovered, provide a subtle visual link (pulse or outline) to the fields it can populate (Composer, Year, Publisher).

### 2. Field-Level Triggers (The Affinity)
- **Inline Magnifier**: Add a small `magnifying-glass` icon inside or next to the `Composers` line edit when it is empty.
- **Empty State Hint**: Display a ghosted placeholder like `Click SEARCH below to lookup...` when a high-priority field is empty.

### 3. Smart Highlighting
- When a user clicks a field like `Composers` and it's empty, a small tooltip or "pill" could appear near the cursor saying "Quick Search Google/MusicBrainz?".

## 📈 Success Criteria
- Boss no longer asks "How do I find the composer?".
- Reduced eyes-off-field movement during the metadata scouting phase.
