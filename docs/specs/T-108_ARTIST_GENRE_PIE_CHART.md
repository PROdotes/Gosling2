---
tags:
  - layer/ui
  - domain/visualization
  - status/spec
  - type/feature
  - size/small
  - value/medium
links:
  - "[[T-17_qualified_artist_view]]"
---
# T-108: Artist Genre Pie Chart

## 1. Objective
Enable users to visualize the genre distribution for a specific artist (or selection of artists) via a pie chart. This helps in understanding the musical profile of an artist within the library.

## 2. User Experience
The feature will be accessible via:
1.  **Side Panel Header**: A stats icon or context menu on the Artist Name label.
2.  **Artist/Entity List**: Right-click context menu on a "Person" or "Group" entity -> "View Statistics".

**Interaction Flow**:
1.  User selects "View Statistics" for artist "Queen".
2.  A dialog `ArtistStatsDialog` opens.
3.  The dialog displays a Pie Chart showing the percentage of songs belonging to each Genre (e.g., Rock: 60%, Pop: 30%, Opera: 10%).
4.  User can close the dialog.

## 3. Technical Architecture

### 3.1 Data Retrieval
We leverage the existing `Unified Artist` graph to fetch all songs associated with an artist identity.

*   **Service Method**: `LibraryService.get_songs_by_unified_artist(artist_name)`
    *   This ensures we capture songs from aliases and group memberships if applicable (depending on resolution logic).
*   **Tag Parsing**:
    *   Iterate through the `Song.tags` list.
    *   Filter strings starting with `Genre:`.
    *   Strip prefix to get raw Genre name.

### 3.2 Visualization Engine
*   **Library**: `matplotlib`
    *   Reason: Standard, robust, easy integration with PyQt via `FigureCanvasQTAgg`.
    *   Requirement: Add `matplotlib` to `requirements.txt`.

### 3.3 UI Components
*   **New Dialog**: `src/presentation/dialogs/artist_stats_dialog.py`
    *   `class ArtistStatsDialog(QDialog)`
    *   **Layout**:
        *   Header: Artist Name (Large Font).
        *   Body: `MatplotlibWidget` (Central Widget).
        *   Footer: "Close" button.
*   **Integration**:
    *   `SidePanelWidget`: Add context menu action to Header Label.
    *   `EntityListWidget`: Add context menu action.

## 4. Implementation Steps

1.  **Dependencies**: Add `matplotlib` to `requirements.txt`.
2.  **Backend**:
    *   Create helper method `LibraryService.get_artist_genre_stats(artist_name: str) -> Dict[str, int]`.
        *   Returns `{ 'Pop': 15, 'Rock': 5 }`.
3.  **Frontend**:
    *   Create `ArtistStatsDialog`.
    *   Implement plotting logic using `matplotlib.pyplot.pie`.
        *   Configure colors to match application theme (Dark Mode friendly).
        *   Add legend.
4.  **Wiring**:
    *   Connect context menus in `SidePanelWidget` and `EntityListWidget`.

## 5. Mockup / Visual Description
```
+--------------------------------------------------+
|  Stats: Queen                                [X] |
+--------------------------------------------------+
|                                                  |
|           /---\                                  |
|          |     |  Rock (60%)                     |
|           \---/   Pop (30%)                      |
|                   Opera (10%)                    |
|                                                  |
+--------------------------------------------------+
|                                          [Close] |
+--------------------------------------------------+
```

## 6. Future Considerations
*   **Clickable Slices**: Clicking "Rock" opens a filter for Queen + Rock songs.
*   **Time Series**: "Genres over Time" line chart (using `recording_year`).
