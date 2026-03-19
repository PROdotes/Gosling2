# COMPREHENSIVE TEST REWRITE PLAN

## Philosophy
Each test is a contract: "WHEN I call X with Y, I expect EXACTLY Z back". Tests fail when contract is violated.

---

## LAYER 1: REPOSITORIES (Raw SQL/Data Access)

Test each repo method with exact inputs/outputs:

| Repo | Method | Test | Expected |
|------|--------|------|----------|
| SongRepository | get_by_id | valid ID | exact Song with exact fields |
| | | invalid ID | None |
| | get_by_title | exact match | exact songs |
| | | partial match | exact songs |
| | | no match | [] |
| | search_surface | query "ever" | exact songs with "ever" in title/album |
| | | query "" | all songs or []? |
| IdentityRepository | search_identities | "Nirvana" | exact identities |
| | | "nirvana" (case) | case-insensitive |
| | get_aliases_batch | identity with aliases | exact aliases |
| | | identity without aliases | [] |
| AlbumRepository | get_by_id | valid | exact Album |
| | | invalid | None |
| PublisherRepository | get_hierarchy_batch | parent chain | exact parent chain |

---

## LAYER 2: SERVICES (Business Logic)

Test each service method with exact behavior:

| Service | Method | Test Cases |
|---------|--------|------------|
| CatalogService | get_song | exists, not found, 0 credits, multiple credits, orphaned (no identity) |
| | search_songs | title match, identity match, alias match, group expansion, no results, empty query |
| | get_songs_by_identity | person (resolves groups), group (resolves members), alias-only, no songs |
| | get_all_identities | exact count, ordering (ASCII), excludes deleted |
| | get_album | exists, not found, no publishers, no songs |
| | get_publisher | parent chain, children, not found |
| | get_publisher_songs | has songs, no songs |
| AuditService | get_history | has data (exact), no data, deleted record, invalid table |
| MetadataService | various | file exists, file not found, corrupt file |

---

## LAYER 3: ROUTERS (HTTP Layer)

Test each endpoint with exact responses:

| Router | Endpoint | Test Cases |
|--------|----------|------------|
| catalog | GET /songs/{id} | 200 with exact SongView, 404 |
| | GET /songs/search?q= | exact results, empty |
| | GET /identities | exact list |
| | GET /identities/{id}/songs | exact songs, 404 |
| | GET /albums | exact albums |
| | GET /publishers | exact publishers |
| audit | GET /history/{table}/{id} | 200 with exact timeline, 404, 500 |
| metabolic | GET /inspect/{id} | 200 with SongView, 404 |

---

## LAYER 4: VIEW MODELS (Transformations)

| Model | Transform | Test |
|-------|-----------|------|
| SongView.from_domain | domain → view | exact display_artist, formatted_duration |
| | | multiple credits → comma-joined |
| | | null duration → "0:00" |
| AlbumView.from_domain | domain → view | exact display_artist, display_publisher |
| | | multi-publisher → "X, Y (Z)" format |

---

## LAYER 5: EDGE CASES (The "What If" Tests)

| Scenario | Test |
|----------|------|
| Empty DB | All list endpoints return [] |
| Orphaned song | Song exists but identity deleted - what happens? |
| Circular groups | Group A → member B, Group B → member A |
| Song with deleted identity | Credit points to deleted identity |
| Very long string | Name > 255 chars |
| Unicode | "Björk", "日本語" |
| Negative ID | get_song(-1) |
| Zero ID | get_song(0) |
| Whitespace query | search_songs(" ") |

---

## LAYER 6: INTEGRATION (End-to-End)

| Flow | Test |
|------|------|
| Search "Nirvana" | HTTP → Router → Service → Repo → hydrate → exact SongView |
| Publisher search | "universal" → returns UMG, Island Def Jam (children) - contract: should/shouldn't include children? |
| Album with songs | GET /albums/{id} → exact songs with exact track numbers |

---

## CONFTEST.PY FIXES NEEDED

Each test should use one of:
1. `empty_db` - clean DB with only schema (for negative tests)
2. `populated_db` - rich dataset with known exact values
3. `edge_case_db` - DB with nulls, orphans, boundary values

populated_db should contain:
- Songs with 0, 1, 2, 5+ credits
- Songs with no album, single album, multi-album
- Songs with no tags, single tag, multi-tag, tags of every category
- Identities that are: person, group, alias-only, member-only
- Publishers with: no parent, single parent, multi-level hierarchy
- Albums with: no publisher, single publisher, multi-publisher

---

## EXECUTION SEQUENCE

1. Fix conftest.py - Add edge_case_db fixture with orphans, nulls, etc.
2. Rewrite test_audit.py - Add all cases (this is where you found the bug)
3. Rewrite test_catalog.py - Exact value verification for all service methods
4. Add test_repositories/ - New folder for repo tests
5. Rewrite test_engine.py - Fix env leaks, add HTTP error tests
6. Rewrite test_search.py - Exact result verification
7. Add edge_case_tests.py - Orphaned data, circular refs, etc.
8. View model tests - Transformation contracts

---

## CURRENT TEST FILES

- test_audit.py
- test_catalog.py
- test_coverage_gap.py
- test_engine.py
- test_engine_search.py
- test_lookup_integrity.py
- test_metadata_parser.py
- test_metadata_service.py
- test_publisher_logic.py
- test_search.py