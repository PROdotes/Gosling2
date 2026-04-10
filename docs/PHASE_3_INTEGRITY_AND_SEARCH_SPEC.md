# PHASE 3: INTERACTIVE INTEGRITY & GLOBAL SEARCH SPEC

## 1. Objective
Refactor the GOSLING2 dashboard to eliminate structural duplication and implement diacritic-agnostic search (e.g., `noë` matching `noe`) across all entity domains.

---

## 2. Frontend: Component Consolidation

### 2.1 The `SearchSelect` Component
- **Problem:** `link_modal.js` and `edit_modal.js` re-implement search input, debounce, keyboard navigation, and dropdown rendering.
- **Action:** Extract logic into `src/static/js/dashboard/components/search_select.js`.

| Responsibility | Implementation |
| :--- | :--- |
| **Input Mode** | Plain text input or generic `<select>` replacement |
| **Search Hook** | Callback to an API `fetcher(query)` |
| **Normalization** | Strips diacritics locally for highlighting/filtering |
| **Keyboard Nav** | Standardized `ArrowUp/Down/Enter/Escape` for all pickers |

### 2.2 Generic Removal Handler
- **Problem:** `main.js` has ~150 lines of identical `if (action === "remove-X")` logic.
- **Action:** Implement `handleLinkRemoval(actionTarget)`, mapping `data-action` to a lookup table of API callers.

---

## 3. Backend: Diacritic-Agnostic Search

### 3.1 The "Shadow Column" Approach
**Goal:** Searching `dragojevic` must match `Dragojević` without a 100% CPU hit on every query.

#### Normalization Logic (`src/utils/text.py`)
```python
import unicodedata
def normalize_for_search(text: str) -> str:
    nfd = unicodedata.normalize('NFD', text)
    return "".join(c for c in nfd if unicodedata.category(c) != 'Mn').lower()
```

#### Database Schema Changes
The following tables will receive a `_Search` column populated by the Service Layer:

1.  **`ArtistNames`** -> `DisplayName_Search` (Matches Artists/Aliases)
2.  **`Songs`** -> `MediaName_Search` (Matches Song Titles)
3.  **`Albums`** -> `Title_Search` (Matches Album Titles)
4.  **`Publishers`** -> `Name_Search` (Matches Publisher Names)
5.  **`Tags`** -> `Name_Search` (Matches Genres/Tags)

### 3.2 Service Layer Hardening
Every "Write" operation in the **Service Layer** will pass incoming names through `normalize_for_search` before they reach the repository. This ensures that:
- Manual dashboard edits are normalized.
- Ingestion imports are normalized.
- Web-crawled metadata is normalized.

---

## 4. Vertical Slice Blueprint (VSB)

| Feature | Input | Condition | Expected Result |
| :--- | :--- | :--- | :--- |
| **Identity Search** | `"noe"` | Match `Noë` | **SUCCESS**: Returns `IdentityID` for 'Noë' |
| **Identity Search** | `"SIME"` | Match `Šime` | **SUCCESS**: Returns `IdentityID` for 'Šime' |
| **Removal** | `Remove Tag` | ID Missing | **ERROR**: Hard 404 (Banker Mode) |
| **Removal** | `Remove Tag` | Authorized | **SUCCESS**: Atomic removal + Re-hydration |

---

## 5. Next Steps
1.  **Migration:** Execute SQL scripts to add and populate `_Search` columns.
2.  **Repo Audit:** Update all `search_X` methods to point to new columns.
3.  **UI Cleanup:** Purge duplicate action handlers and initialize `SearchSelect` in `main.js`.
