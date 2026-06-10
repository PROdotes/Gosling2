# Multi-Edit Spec (v2)

## Core idea

The song detail view never knows it's editing multiple songs. It renders a
**virtual song** built by collapsing the selection, and sends the same shaped
edits it sends today. Multi-ness is hidden entirely behind the interface: the
multi-edit service is a deep module whose interface is "one song's worth of
view and edits, plus a `song_ids` list," and whose implementation absorbs all
the fan-out, conflict detection, and per-song ID resolution. Two parts:

- **Collapser (read)**: merges N songs into one view, flagging disagreements.
- **Packer (write)**: takes one single-song-shaped operation plus a list of
  `song_ids`, expands it into per-song mutation items, and hands the batch to
  the existing `MutationCoordinator`. The coordinator is unchanged — it already
  applies a batch of items in one transaction with full rollback.

The seam stays at the existing HTTP interface; the frontend learns two new
endpoints and zero new concepts. Deletion test: remove this module and every
caller re-grows collapse/fan-out/ID-resolution logic — it earns its keep.

## Scope

Songs only (v1). Triggered when 2+ songs are selected in the song list.

---

## Read: Collapsed View

**New endpoint**: `POST /api/v1/songs/multi-view`
**Body**: `{ "song_ids": [1, 2, 3] }`

**Response: a plain `SongView`** — no new view models. The virtual song IS a
`SongView`; the detail view renders it with the exact code it has today. The
multi-ness is carried by two small extensions to existing models:

- `SongView.mixed_fields: dict[str, list] = {}` — keys are the scalar fields
  that disagree across the selection; values are the distinct values present
  (null = some songs empty). Empty dict for single songs.
- `universal: bool = True` on `SongCredit`, `Tag`, `Publisher`, `SongAlbum` —
  defaults `True`, so every existing single-song path serializes unchanged.

Service fetches all songs (`SongRepository.get_by_ids`), hydrates each, and
collapses. All collapsing logic lives in the service layer — the frontend
only reads the two flags.

### Scalar fields (`media_name`, `bpm`, `year`, `isrc`, `notes`)

- All songs agree → field carries the value, not in `mixed_fields`.
- Any disagreement → field is `null`, and `mixed_fields["year"] = [1999, 2001]`.
- Frontend renders mixed as an empty input with `placeholder` ghost text —
  `Mixed: 1999, 2001` (or just `Mixed` where values are long, e.g. notes).
  `placeholder` accepts text even on number inputs, so no type juggling.
- Mixed scalars **are editable** — typing a value overwrites it on all
  selected songs (covers the "one of them is a typo" case). An untouched
  mixed field is simply not included in the save payload (`exclude_none`
  contract, same as single-song edit).

### M2M fields (credits, tags, publishers, albums)

Union of all entries across selected songs, in the normal `SongView` lists.
Each entry's `universal` flag:

- `universal: true` — present on **all** songs. Rendered as a normal chip,
  removable.
- `universal: false` — present on **some** songs. Rendered as a **locked
  chip**: dimmed/striped, no remove control. Visible for feedback, not
  editable in multi-edit. Not a new component — the existing chip with a
  locked state driven by the flag.

A credit entry is identified by `(name_id, role_name)` — Artist B as Performer
and Artist B as Composer are two separate entries. Union entries carry the
first song's per-song row IDs (`credit_id`, `source_id`); these are
meaningless across the selection and the multi-mutate path never uses them.

---

## Write: the Packer

**New endpoint**: `POST /api/v1/songs/multi-mutate`
**Body**: `{ "song_ids": [...], <single-song-shaped op without song_id> }`
(exact body shape per op mirrors the existing mutate item models)

The packer is **not a mutator** and adds **no new item types**. It is a pure
expansion step: turn the op into one existing mutation item per song
(`UpdateSongItem`, `AddTagItem`, `RemoveCreditItem`, ...), build a single
`MutationRequest`, call `MutationCoordinator.apply()`. The coordinator, its
dispatch table, and the mutators are untouched — they already loop items in
one transaction and run the per-touched-song ID3/filing pass afterward.

### Scalars

One `UpdateSongItem` per song, carrying only the fields the user touched.

### M2M deltas (server-side, in the packer)

- **Add** (tag/credit/publisher/album): songs that already have it → skip
  (idempotent); songs that don't → add item. Adding always targets **all**
  selected songs.
- **Remove**: only offered for `universal: true` entries, so every song has
  it. The packer resolves per-song row IDs internally (e.g. each song's
  `CreditID` for a `(name_id, role)` pair) and emits one remove item per song.
- Album links added via multi-edit default to `track_number=0, disc_number=0`
  (the packer sets these explicitly — `AddAlbumItem` does not default them).

The frontend never loops over songs and never sees per-song IDs.

---

## Selection model (general-table semantics)

Checkboxes are removed. The song list behaves like a native list widget
(Explorer/Finder): selection is row-level, with two pieces of state —

- **Selection**: the set of highlighted rows. Drives the editor panel:
  1 selected = single-song editor, 2+ = collapsed multi view.
- **Focus (cursor)**: exactly one row, the last clicked/arrowed-to row.
  Drawn as a thin outline; purely navigational, never drives the editor
  by itself.

Bindings:

| Input | Effect |
|---|---|
| Click | select that row only (collapse selection), focus it |
| Ctrl+Click | toggle row in/out of selection, focus it |
| Shift+Click | select range from anchor to row |
| Up/Down | move focus, collapse selection to focused row |
| Shift+Up/Down | move focus, extend range from anchor |
| Ctrl+Up/Down | move focus only, selection untouched |
| Ctrl+Space | toggle focused row in/out of selection |
| Ctrl+A | select all displayed rows |
| Escape | clear selection, blank the editor |

Plain click/arrow collapsing a multi-row selection is accepted standard
behavior (Ctrl variants exist to preserve it). The anchor is set by the
last non-shift selection action.

## UX summary

| State | Display | Editable |
|---|---|---|
| Scalar, agreed | normal value | yes — overwrites all |
| Scalar, mixed | blank + ghost `Mixed: <values>` | yes — overwrites all; untouched = excluded |
| M2M, universal | normal chip | removable |
| M2M, partial | locked chip (dimmed, no remove) | no |
| M2M, add | normal add flow | adds to all songs |

---

## New Files

| File | Purpose |
|---|---|
| `src/engine/routers/multi_edit.py` | `multi-view` + `multi-mutate` endpoints (request models live here, same pattern as `mutation_models.py`) |
| `src/services/multi_edit_service.py` | Collapser (read) + Packer (write → MutationCoordinator) |

No new view models: `SongView` gains `mixed_fields`, and the four M2M models
gain `universal` (default `True`).
