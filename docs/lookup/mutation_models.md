# Mutation Models
*Location: `src/engine/routers/mutation_models.py`*

**Responsibility**: Pydantic models for the unified mutation protocol.

---

## MutationRequest
The main payload for `POST /api/v1/mutate`.
- `add: List[Union[AddCreditItem, AddTagItem, AddPublisherItem, AddAlbumItem]]`
- `remove: List[Union[RemoveCreditItem, RemoveTagItem, RemovePublisherItem, RemoveAlbumItem]]`
- `update: List[Union[UpdateSongItem, UpdateTagEntityItem, UpdateSongTagItem, UpdateSongAlbumItem, UpdateAlbumEntityItem, UpdateCreditEntityItem, UpdatePublisherEntityItem]]`
- `delete: List[Union[DeleteSongItem, DeleteTagItem, DeletePublisherItem, DeleteAlbumItem, DeleteIdentityItem, DeleteOriginalFileItem]]`

---

## Add Items

### AddCreditItem
`{ type: "credit", song_id: int|None, album_id: int|None, name: str, id: int|None, role: str }`
- At least one of `song_id` or `album_id` must be present.

### AddTagItem
`{ type: "tag", song_id: int, id: int|None, name: str|None, category: str|None }`
- Either `id` or both `name` and `category` must be present.

### AddPublisherItem
`{ type: "publisher", song_id: int|None, album_id: int|None, id: int|None, name: str|None }`
- Either `id` or `name` must be present.

### AddAlbumItem
`{ type: "album", song_id: int, id: int|None, name: str|None, album_type: str|None, release_year: int|None, track_number: int|None, disc_number: int|None }`

### AddIdentityMemberItem
`{ type: "identity_member", group_id: int, member_id: int }`

### AddIdentityAliasItem
`{ type: "identity_alias", identity_id: int, display_name: str|None, name_id: int|None }`
- Either `display_name` or `name_id` must be present.

---

## Update Items

### UpdateSongItem
`{ type: "song", id: int, media_name: str|None, year: int|None, bpm: int|None, isrc: str|None, is_active: bool|None, processing_status: int|None, move_to_library: bool|None }`

### UpdateTagEntityItem
`{ type: "tag_entity", id: int, name: str|None, category: str|None }`

### UpdateSongTagItem
`{ type: "song_tag", song_id: int, tag_id: int, is_primary: bool }`

### UpdateSongAlbumItem
`{ type: "song_album", song_id: int, album_id: int, track_number: int|None, disc_number: int|None }`

### UpdateAlbumEntityItem
`{ type: "album_entity", id: int, name: str|None, album_type: str|None, release_year: int|None }`

### UpdateCreditEntityItem
`{ type: "credit_entity", id: int, name: str }`

### UpdatePublisherEntityItem
`{ type: "publisher_entity", id: int, name: str|None, parent_id: int|None }`

### UpdateIdentityItem
`{ type: "identity", id: int, identity_type: str|None }`
- `identity_type` must be `"person"` or `"group"` if provided.

---

## Remove Items

### RemoveCreditItem
`{ type: "credit", id: int, song_id: int|None, album_id: int|None }`

### RemoveTagItem
`{ type: "tag", song_id: int, id: int }`

### RemovePublisherItem
`{ type: "publisher", id: int, song_id: int|None, album_id: int|None }`

### RemoveAlbumItem
`{ type: "album", song_id: int, id: int }`

### RemoveIdentityMemberItem
`{ type: "identity_member", group_id: int, member_id: int }`

### RemoveIdentityAliasItem
`{ type: "identity_alias", identity_id: int, name_id: int }`

---

## Delete Items

### DeleteSongItem
`{ type: "song", id: int }`

### DeleteTagItem
`{ type: "tag", id: int|None, unlinked: bool|None }`

### DeletePublisherItem
`{ type: "publisher", id: int|None, unlinked: bool|None }`

### DeleteAlbumItem
`{ type: "album", id: int|None, unlinked: bool|None }`

### DeleteIdentityItem
`{ type: "identity", id: int|None, unlinked: bool|None }`

### DeleteOriginalFileItem
`{ type: "original_file", song_id: int }`

---

## Shared Validators

### not_empty(v)
Ensures strings are not just whitespace.

### exactly_one_target(v, info)
Ensures only one of `song_id` or `album_id` is set where appropriate.

### id_or_unlinked(v, info)
Ensures either an ID is provided or `unlinked=True`.

### id_or_name_and_category(v, info)
Ensures either an ID is provided or both name and category are present for tags.

### name_required_without_id(v, info)
Ensures a name is provided if no ID is given for entities.

### at_least_one_change(v, info)
Ensures a request isn't empty.

### year_range(v)
1860 to current+1.

### bpm_positive(v)
1 to 500.

### isrc_format(v)
12-char alphanumeric.

### media_name_not_empty(v)
Specific validator for Song media name.

### name_or_id(v)
Ensures either `display_name` or `name_id` is provided for `AddIdentityAliasItem`.

### valid_type(v)
Ensures `identity_type` is `"person"` or `"group"` for `UpdateIdentityItem`.

---

## Merge Items

### MergeIdentityItem
`{ type: "merge_identity", source_id: int, target_id: int }`

### MergePublisherItem
`{ type: "publisher_merge", source_id: int, target_id: int }`

### MergeTagItem
`{ type: "tag_merge", source_id: int, target_id: int }`
