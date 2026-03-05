# [GOSLING3] v3core Repository Specification

This document defines the stateless, ghost-free API for the direct database layer in Gosling3.

## 1. Design Philosophy
- **Stateless**: The Repository does not "manage state." It executes SQL and returns DTOs (Data Transfer Objects).
- **Narrow Focus**: No UI logic, No file system logic. Pure SQLite interaction.
- **Fail-Fast**: If the database column doesn't match the DTO, it crashes with a `SchemaError` instead of returning a partial object.

## 2. SongRepository methods

### `get_all_songs() -> List[Song]`
Returns every active song in the library. This replaces the complex "Yellberus" `BASE_QUERY`.

### `get_song_by_id(int) -> Song`
Fetches a single song with its full credit set and primary album. If any required field is missing, it raises a `ValidationException`.

### `update_song_metadata(song_id: int, updates: Dict[str, Any]) -> None`
Performs atomic SQL updates. This is the **ONLY** way to change a song. 
- *Constraint*: Cannot update credits through this method (use `CreditService`).

## 3. IdentityRepository methods

### `resolve_active_identity_set(source_id: int) -> Set[int]`
The core "Freddie Paradox" resolver. 
1.  Joins `SongCredits` -> `ArtistNames` -> `Identities`.
2.  Follows `GroupMemberships` (both directions).
3.  Returns a set of `IdentityIDs`.

### `merge_identities(source_id: int, target_id: int) -> int`
The "Scar Healing" method.
1.  Updates all `ArtistNames` linked to `source_id` to point to `target_id`.
2.  Updates `GroupMemberships`.
3.  Deletes the empty `source_id` identity.
4.  Returns the `target_id`.

## 4. Why this stops the "Divergence"?
1.  **Divergence is impossible**: We don't have a separate `Registry` (Yellberus). The `Song` DTO is the registry.
2.  **No Ghost Data**: The repository only queries columns that are explicitly defined in the `MODELS.md` Pydantic models.
3.  **Atomic Operations**: By splitting "Metadata Update" from "Credit Update," we avoid the "Spaghetti Merge" bug where changing a title accidentally wipes the composer credits.
