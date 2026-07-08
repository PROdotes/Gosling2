# Junk Detector (Duplicates)
*Location: documentation only*

---

## 1. Documentation Pass-Throughs (Stale Debt)
*Service methods that are 1:1 wrappers for Repo methods. These methods do not perform transformation or orchestration beyond transaction management. Detailed documentation resides in `docs/lookup/data.md`.*

| Service Method | Repo Target | Note |
| :--- | :--- | :--- |
| `get_all_roles()` | `SongCreditRepository.get_all_roles()` | Pass-through. |
| `get_tag_categories()` | `TagRepository.get_categories()` | Pass-through. |
| `get_all_tags()` | `TagRepository.get_all()` | Pass-through (no hydration). |
| `search_songs_slim(query)` | `SongRepository.search_slim(query)` | Pass-through. |
| `search_albums_slim(query)` | `AlbumRepository.search_slim(query)` | Pass-through. |
| `get_all_identities_slim()` | `IdentityService.get_all_slim()` | Pass-through; the live identity-list path is slim (no hydration). The old hydrating `get_all_identities()` note is obsolete. |

## 2. Structural Logic Duplication
*Identical logic implemented in multiple locations in `src/`. These are candidates for refactoring into a Base class or shared utility.*

- **Artist Resolution**: `SongCreditRepository` and `AlbumCreditRepository` both implement `get_or_create_credit_name` logic (via cross-instantiation). The `ArtistNames` table is the source of truth, but the logic is bound to the `SongCreditRepository`.
- **Credit Linkage**: `add_credit` methods perform near-identical checks before writing to `SongCredits` vs `AlbumCredits`. Candidates for a `BaseCreditRepository`.

## 3. Name Ambiguity
*Identical method names with different return contexts but similar purposes.*

- `get_by_path`:
  - `MediaSourceRepository`: Returns `MediaSource` (Base Record).
  - `SongRepository`: Returns `Song` (Specialized Record).
- `get_by_hash`:
  - `MediaSourceRepository`: Returns `MediaSource` (Base Record).
  - `SongRepository`: Returns `Song` (Specialized Record).
- `search_slim`:
  - `SongRepository`: Returns `List[dict]` for song list-view.
  - `AlbumRepository`: Returns `List[dict]` for album list-view.
