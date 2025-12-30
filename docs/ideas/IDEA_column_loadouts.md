---
tags:
  - layer/ui
  - domain/table
  - status/future
  - type/feature
  - size/small
links:
  - "[[T-15_column_customization]]"
  - "[[PROPOSAL_LIBRARY_VIEWS]]"
---
# Column Loadouts

Named layout presets for different workflows.

## Concept

Save and switch between named layout configurations:
- **"Editing"** — All metadata columns visible, side panel expanded
- **"Browsing"** — Just Title, Artist, Duration, sidebar collapsed
- **"Metadata Audit"** — FilePath, ISRC, Genre, Language visible

## UI

- Dropdown in library toolbar: `[Editing ▼]`
- "Save as Loadout..." option in header context menu
- "Manage Loadouts..." dialog for rename/delete

## Settings Structure

```json
{
  "library/layouts": {
    "_active": "default",
    "default": {
      "columns": {
        "order": [0, 1, 2, 3, 4, 5, 6, 7, 8],
        "hidden": []
      }
    },
    "Editing": {
      "columns": {
        "order": [0, 2, 1, 3, 4, 5, 6, 7, 8],
        "hidden": []
      },
      "splitters": {
        "sidebar": 250,
        "side_panel": 300
      }
    },
    "Browsing": {
      "columns": {
        "order": [0, 1, 3, 2, 4, 5, 6, 7, 8],
        "hidden": [2, 4, 5, 6, 7, 8]
      },
      "splitters": {
        "sidebar": 0,
        "side_panel": 0
      }
    }
  }
}
```

**Key design decisions:**
- `order` includes ALL columns — hidden columns keep their position
- When unhiding a column, it returns to its saved position (not appended to end)
- Loadouts are extensible: can add `splitters`, `window`, `filters`, etc.

## Future Extensions

| Property | Purpose |
|----------|---------|
| `columns.order` | Visual order of all columns |
| `columns.hidden` | Which columns are hidden |
| `columns.widths` | Column widths (optional) |
| `splitters.sidebar` | Left sidebar width |
| `splitters.side_panel` | Right panel width |
| `window.size` | Window dimensions |
| `window.position` | Window position |
| `filters.type_tab` | Active type tab |
| `filters.search` | Saved search text |

## Implementation Notes

- T-15 (Column Customization) establishes the base structure
- This feature adds the UI for switching and naming layouts
- Low effort once T-15 is done

## Depends On

- [[T-15_column_customization]] — Base persistence (MVP)
