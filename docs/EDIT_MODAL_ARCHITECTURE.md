# Edit Modal Architecture

## Overview

The edit modal is a reusable, config-driven component for editing any linked entity chip in the detail panel. It was built publisher-first but is fully generic — wiring up credits, tags, albums, etc. is purely additive.

---

## Files

| File | Role |
|------|------|
| `src/templates/dashboard.html` | `#edit-modal` overlay element — reuses `.link-modal-*` CSS classes |
| `src/static/css/dashboard.css` | `.edit-modal-field`, `.edit-modal-section-title`, `.link-chip-label` |
| `src/static/js/dashboard/components/edit_modal.js` | The modal component — `openEditModal(config, triggerEl)` / `closeEditModal()` |
| `src/static/js/dashboard/main.js` | Click handler for `open-edit-modal` / `close-edit-modal` actions |
| `src/static/js/dashboard/renderers/songs.js` | Chip names rendered as `<button class="link-chip-label" data-action="open-edit-modal">` |

---

## How It Works

### Opening

A chip name is rendered as a button:
```html
<button class="link-chip-label"
        data-action="open-edit-modal"
        data-chip-type="publisher"
        data-item-id="${p.id}">
    ${name}
</button>
```

The document click handler in `main.js` catches `open-edit-modal`, builds a config object for the chip type, and calls `openEditModal(config, actionTarget)`.

`actionTarget` is passed as `triggerEl` — when a rename succeeds, the modal automatically updates the chip label in the detail panel via `triggerEl.textContent = newName`.

### Config Shape

```js
openEditModal({
    title: string,                         // modal header e.g. "Edit Publisher"
    name: string,                          // current name, pre-fills the rename input
    onRename: async (newName) => {},       // called on blur/Enter; null = not renameable
    onClose: () => {},                     // called when modal fully closes — refresh detail panel
    category: {                            // null if no category field
        label: string,
        value: string,
        editable: bool,                    // true = editable input, false = read-only label
        onSave: async (val) => {},
    } | null,
    children: {                            // null if no children section
        label: string,                     // section heading e.g. "Sub-publishers"
        items: [{ id, label }],            // MUST be the live array — modal mutates it in place
        onSearch: async (q) => [{ id, label }],
        onAdd: async (opt) => {},          // opt = { id, label } for existing; { id:null, rawInput } for new
        onRemove: async (item) => {},
        onRenameChild: async (item, newName) => {},  // called when a child chip is renamed
        createLabel: (q) => string,
    } | null,
}, triggerEl)
```

### Important: `children.items` must be a live reference

The modal holds `_childItems = _config.children.items` — the same array reference. `onAdd` pushes to it, `onRemove` splices from it (in place, never reassigns). If you pass a copy (`[...arr]`), add/remove will work visually but won't sync between `main.js` and the modal.

### onClose and detail panel refresh

`onClose` is always `refreshActiveDetail` (defined in `main.js`). It reads `activeDetailKey` (e.g. `"songs:42"`) and re-opens the correct detail panel for whatever mode is active. This is generic — works from song detail, album detail, artist detail, etc. `onClose` is NOT called when returning from a child edit — only on full modal close.

### Rename flow

1. User edits name input → blur or Enter fires `commitRename`
2. `commitRename` checks `_lastCommittedName` guard (no double-save)
3. Calls `onRename(newName)` → PATCH endpoint (204, no body)
4. On success: updates `_config.name`, updates `triggerEl.textContent` in the detail panel
5. If in a child edit (`_parentSnapshot` exists), auto-closes back to parent
6. Detail panel is NOT re-rendered during rename — chip updates in place, no flicker

### Child edit (one level deep)

Clicking a child chip label opens a rename-only sub-modal using the same `#edit-modal` element:

1. `openChildEdit(item)` saves the full parent state to `_parentSnapshot`
2. Calls `openEditModal` with a minimal config (`children: null`, `onClose: null`)
3. On Enter/Escape/✕ → `closeEditModal` sees `_parentSnapshot`, restores parent modal
4. `onRenameChild(item, newName)` in the parent config handles the PATCH; `item.label` is updated in the live array so the parent re-renders correctly
5. No further drill-down — child edit is always rename-only

### Gotchas

- `_navigating = true` is set during `openChildEdit` and `closeEditModal` restore to suppress blur-triggered `commitRename` while the modal content is being swapped
- `_suppressNextOverlayClick = true` is set in `openChildEdit` and `selectChildOption` to swallow the ghost click that fires on the overlay after a dropdown/chip interaction removes the clicked element from the DOM
- Already-linked items are filtered from the child search dropdown (prevents duplicates)
- Error messages stay visible for 6 seconds

### Close flow

1. ✕ button (`data-action="close-edit-modal"`) or click on overlay backdrop
2. If `_parentSnapshot` exists → restore parent modal (child edit back-navigation)
3. Otherwise → hide overlay, clear state, call `onClose()` → `refreshActiveDetail()`

---

## Backend

### View Models

Publisher and tag endpoints return view models, not domain models:

- `PublisherView` — `id`, `name`, `parent_name`, `sub_publishers: List[PublisherView]`
- `TagView` — `id`, `name`, `category`

These are defined in `src/models/view_models.py` and used by all `GET /publishers*` and `GET /tags*` endpoints.

### `AddPublisherBody` / `AddTagBody`

Both support Truth-First linking — pass an ID to link an existing record, or a name to get-or-create:

```json
{ "publisher_id": 5 }           // link existing by ID
{ "publisher_name": "Sub Pop" } // get-or-create by name

{ "tag_id": 3 }                             // link existing by ID
{ "tag_name": "Grunge", "category": "Genre" } // get-or-create by name
```

### `setPublisherParent`

- **Repo**: `PublisherRepository.set_parent(publisher_id, parent_id, conn)` — sets `ParentPublisherID`
- **Service**: `CatalogService.set_publisher_parent(publisher_id, parent_id)`
- **Router**: `PATCH /api/v1/publishers/{id}/parent` — body `{ parent_id: int | null }`
- **api.js**: `setPublisherParent(publisherId, parentId)`

Setting `parent_id: null` unlinks a sub-publisher.

---

## Wiring a New Chip Type

### 1. Backend (if endpoints don't exist)

Check `docs/lookup/engine_routers.md` — add/remove/update endpoints follow the pattern:
- `POST /api/v1/songs/{id}/{type}` — add link
- `DELETE /api/v1/songs/{id}/{type}/{link_id}` — remove link
- `PATCH /api/v1/{type}/{id}` — update record globally

Add repo method → service method → router endpoint → `api.js` helper.

### 2. Render chips as clickable buttons (`songs.js`)

```js
<span class="link-chip">
    <button class="link-chip-label"
            data-action="open-edit-modal"
            data-chip-type="TAG_TYPE_HERE"
            data-item-id="${item.id}">
        ${escapeHtml(item.name)}
    </button>
    <button class="link-chip-remove" data-action="remove-TAG_TYPE_HERE" ...>✕</button>
</span>
```

Also add a `+ Add` button for the section:
```html
<button class="section-add-btn" data-action="open-link-modal" data-modal-type="TAG_TYPE_HERE" data-song-id="${song.id}">+ Add</button>
```

### 3. Add `open-edit-modal` branch in `main.js`

Inside the `if (action === "open-edit-modal")` handler, add a new `chipType` branch. `onClose` is already defined as `refreshActiveDetail` above all branches — just use it.

Fetch fresh detail data rather than relying on the cached list — this ensures name/category are current even if the cache is stale:

```js
if (chipType === "tag") {
    const tagDetail = await getTagDetail(itemId).catch(() => null);
    if (!tagDetail) return;

    openEditModal({
        title: "Edit Tag",
        name: tagDetail.name,
        onRename: async (newName) => {
            await updateTag(itemId, newName, tagDetail.category);
            tagDetail.name = newName;
        },
        onClose,
        category: {
            label: "Category",
            value: tagDetail.category,
            editable: true,
            onSave: async (val) => {
                await updateTag(itemId, tagDetail.name, val);
                tagDetail.category = val;
            },
        },
        children: null,
    }, actionTarget);
}
```

### 4. Wire `open-link-modal` for the + Add button (`main.js`)

Inside `if (action === "open-link-modal")`, add a branch for the new `modalType`.

---

## Chip Types Status

| Chip Type | Rendered as button | Edit modal | + Add (link_modal) | Notes |
|-----------|-------------------|------------|-------------------|-------|
| Publisher | ✅ | ✅ | ✅ | Sub-publishers children list; child rename wired |
| Credit | ❌ | ❌ | ❌ | `role_name` is read-only; `display_name` renameable globally via `update_credit_name` |
| Tag / Genre | ✅ | ✅ | ✅ | `name` + `category` both editable; Truth-First add (ID or name+category) |
| Album | ❌ | ❌ | ❌ | Most complex — track/disc numbers live on the link, not the album record |

---

## Known Limitations

- **Create-new sub-publisher** not supported. The create-new dropdown option appears but `opt.id` is null so `setPublisherParent` is a no-op. Needs a create-and-link endpoint.
- **Albums** will need extra fields on the link (track/disc numbers) — the children pattern won't cover that; likely needs a custom inline form within the chip or a dedicated modal.
