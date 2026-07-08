# Identity normalization gap (diacritics create duplicate identities)

`get_or_create_credit_name` in `src/data/song_credit_repository.py` looks up
`DisplayName = ? COLLATE UTF8_NOCASE` — exact character match, no diacritic stripping. So
"Alexandra Capitanescu" and "Alexandra Căpitănescu" created two separate `Identities` rows
(IDs 799 and 818) instead of resolving to one.

Root cause: Phase 3.1 normalization added `DisplayName_Search` as a shadow column for search, but
the get-or-create lookup was never updated to consult it before inserting a new identity.

## Consequences

- Duplicate identity records for the same person entered with/without diacritics.
- `find_duplicate_groups` in `song_repository.py` keys the performer signature on
  `OwnerIdentityID`, so same-title songs by the "two" identities are NOT flagged as duplicates.
  Confirmed live: "Choke Me" (song 283, identity 799) vs (song 433, identity 818) not caught.

## Fix (agreed direction)

1. In `get_or_create_credit_name`: when the `UTF8_NOCASE` lookup misses, do a secondary check on
   `DisplayName_Search = normalize(display_name)` before creating a new identity.
2. In `find_duplicate_groups`: switch the performer signature from `OwnerIdentityID` to
   `DisplayName_Search` so normalized names collapse. Confirmed working in a manual query test.

## Also noted

- Song 433 has `MediaName_Search = NULL` — an ingest path didn't write the normalized title; hurts search.
- The mark-as-done transition is the right place to run a duplicate check (not every mutation);
  a post-done warning should surface potential dupes before the song is filed away.
- Blocks/degrades the planned fuzzy duplicate-song report wanted before the Jazler import.
