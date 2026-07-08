# Mutation Models
*Location: `src/engine/routers/mutation_models.py`*

**Responsibility**: Pydantic models for the unified mutation protocol (`POST /api/v1/mutate`). All unions are discriminated on `type`.

---

## MutationRequest
All five lists optional; `at_least_one_change` requires at least one non-empty list.
- `add: List[AddCreditItem | AddTagItem | AddPublisherItem | AddAlbumItem | AddIdentityMemberItem | AddIdentityAliasItem]`
- `update: List[UpdateSongItem | UpdateTagEntityItem | UpdateSongTagItem | UpdateSongAlbumItem | UpdateAlbumEntityItem | UpdateCreditEntityItem | UpdatePublisherEntityItem | UpdateIdentityItem]`
- `merge: List[MergeIdentityItem | MergePublisherItem | MergeTagItem]`
- `remove: List[RemoveCreditItem | RemoveTagItem | RemovePublisherItem | RemoveAlbumItem | RemoveIdentityMemberItem | RemoveIdentityAliasItem]`
- `delete: List[DeleteSongItem | DeleteTagItem | DeletePublisherItem | DeleteAlbumItem | DeleteIdentityItem | DeleteOriginalFileItem]`

---

## Add Items

### AddCreditItem
`{ type: "credit", song_id: int|None, album_id: int|None, name: str, id: int|None, role: str }`
- `name` and `role` must not be blank; exactly one of `song_id`/`album_id`.

### AddTagItem
`{ type: "tag", song_id: int, name: str|None, id: int|None, category: str|None, make_primary: bool = False }`
- Either `id` or both `name` and `category`.

### AddPublisherItem
`{ type: "publisher", song_id: int|None, album_id: int|None, name: str, id: int|None }`
- `name` must not be blank; exactly one of `song_id`/`album_id`.

### AddAlbumItem
`{ type: "album", song_id: int, name: str|None, id: int|None, album_type: str|None, release_year: int|None, track_number: int|None, disc_number: int|None, make_primary: bool = False }`
- `name` required when `id` is not provided.

### AddIdentityMemberItem
`{ type: "identity_member", group_id: int, member_id: int }`

### AddIdentityAliasItem
`{ type: "identity_alias", identity_id: int, display_name: str|None, name_id: int|None }`
- Either `display_name` or `name_id`.

---

## Update Items

### UpdateSongItem
`{ type: "song", id: int, media_name: str|None, bpm: int|None, year: int|None, isrc: str|None, is_active: bool|None, processing_status: int|None, source_path: str|None, notes: str|None }`
- `media_name` may not be empty string (null to clear); `year` in `[YEAR_MIN, YEAR_MAX]`; `bpm` bounds from `SCALAR_VALIDATION["bpm"]`; ISRC = 2 country + 3 registrant + 7 digits.
- TODO in code: split into UpdateMediaItem/UpdateSongItem when the MediaMutator boundary is designed.

### UpdateTagEntityItem
`{ type: "tag", id: int, name: str|None, category: str|None }`

### UpdateSongTagItem
`{ type: "song_tag", song_id: int, tag_id: int, is_primary: bool|None }`

### UpdateSongAlbumItem
`{ type: "song_album", song_id: int, album_id: int, track_number: int|None, disc_number: int|None, is_primary: bool|None }`

### UpdateAlbumEntityItem
`{ type: "album", id: int, title: str|None, album_type: str|None, release_year: int|None }`
- Note the field is `title`, not `name`; `release_year` in `[YEAR_MIN, YEAR_MAX]`.

### UpdateCreditEntityItem
`{ type: "credit", id: int, display_name: str|None, song_id: int|None }`

### UpdatePublisherEntityItem
`{ type: "publisher", id: int, name: str|None, parent_id: int|None }`

### UpdateIdentityItem
`{ type: "identity", id: int, identity_type: str|None }`
- `identity_type` must be `"person"` or `"group"` if provided.

---

## Merge Items

### MergeIdentityItem
`{ type: "identity_merge", source_name_id: int, target_name_id: int }`
- Keyed by ArtistName IDs, not Identity IDs.

### MergePublisherItem
`{ type: "publisher_merge", source_id: int, target_id: int }`

### MergeTagItem
`{ type: "tag_merge", source_id: int, target_id: int }`

---

## Remove Items

### RemoveCreditItem
`{ type: "credit", song_id: int|None, album_id: int|None, id: int }`
- Exactly one of `song_id`/`album_id`.

### RemoveTagItem
`{ type: "tag", song_id: int, id: int }`

### RemovePublisherItem
`{ type: "publisher", song_id: int|None, album_id: int|None, id: int }`
- Exactly one of `song_id`/`album_id`.

### RemoveAlbumItem
`{ type: "album", song_id: int, id: int }`

### RemoveIdentityMemberItem
`{ type: "identity_member", group_id: int, member_id: int }`

### RemoveIdentityAliasItem
`{ type: "identity_alias", identity_id: int, name_id: int }`

---

## Delete Items (entity-level soft-delete)

All except `DeleteOriginalFileItem` accept either an explicit `id` or `unlinked=True` (bulk-delete all unlinked entities of that kind).

### DeleteSongItem
`{ type: "song", id: int|None, unlinked: bool = False, delete_file: bool = False }`

### DeleteTagItem
`{ type: "tag", id: int|None, unlinked: bool = False }`

### DeletePublisherItem
`{ type: "publisher", id: int|None, unlinked: bool = False }`

### DeleteAlbumItem
`{ type: "album", id: int|None, unlinked: bool = False }`

### DeleteIdentityItem
`{ type: "identity", id: int|None, unlinked: bool = False }`

### DeleteOriginalFileItem
`{ type: "original_file", song_id: int }`

---

## Shared Validators

### not_empty(v)
Required strings must not be blank (add items). Update items instead use `_reject_empty_string`: optional strings may be null (clear) but never `""`.

### exactly_one_target(v, info)
Exactly one of `song_id`/`album_id` must be set (credit/publisher add + remove items).

### id_or_unlinked(v, info)
Delete items need an `id` or `unlinked=True`.

### id_or_name_and_category(v, info)
AddTagItem: either an ID, or both name and category.

### name_required_without_id(v, info)
AddAlbumItem: a name is required if no ID is given.

### name_or_id(v)
AddIdentityAliasItem: either `display_name` or `name_id`.

### valid_type(v)
UpdateIdentityItem: `identity_type` must be `"person"` or `"group"`.

### year_range(v)
`YEAR_MIN` to `YEAR_MAX` from config (1860 to current+1).

### bpm_positive(v)
Bounds from `SCALAR_VALIDATION["bpm"]` in config (currently 1-300).

### isrc_format(v)
Pattern `^[A-Z]{2}[A-Z0-9]{3}\d{7}$` (2 country + 3 registrant + 7 digits).

### media_name_not_empty(v)
UpdateSongItem: `media_name` may be null (no change) but never empty string.

### at_least_one_change(v, info)
MutationRequest must contain at least one item across the five lists.
