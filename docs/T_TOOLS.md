
# T-Tools: External Entity Management (Inventory)

## Objective
Provide global visibility and management tools for Artists, Albums, and Publishers independent of the Song Context, addressing the "Dead Entity" and "Inventory Blindness" issues.

## Design Concept
- **Access**: Dropdown/Menu in the Side Panel (near Editor/Tools area).
- **Features**:
  - **Global Artist List**: Browse all artists, filter by Type (Person/Group), view Song Count.
  - **Dead Entity Finder**: Identify and bulk-delete orphaned Artists/Publishers (0 linked songs).
  - **Album Vault**: Standalone access to Album Manager with filtering (e.g. "Show Empty Albums").
  - **Publisher Index**: Manage Publisher entities and their aliases.

## Implementation Plan
1. **Refactor Managers**: Ensure `ArtistManager`, `AlbumManager`, etc. can run in "Standalone Mode" (no context song).
2. **Create Tools Menu**: Update Side Panel UI to include a Tools dropdown.
3. **Implement Orphan Logic**: Add repository methods to find entities with `COUNT(songs) == 0`.
4. **Visual Overhaul**: Align these new managers with the "Dark Pro Console" aesthetic.
