# TDD Standard

**One rule above all: tests are reviewed and approved by the user before any implementation is written.**

**"Present tests for review" means: write them directly to the file. The user reviews in their editor — one read, from source. Never show the same test code in chat before writing it, after writing it, or as a summary. Repetition causes the user to skim and miss hallucinations.**

---

## The Workflow (Non-Negotiable)

```
1. Build the feature chain (see below)
2. Check chain against existing code — fill in what exists, flag what's missing
3. Present refined chain to user for review
4. Discuss methods and contracts with user
5. Write ALL tests for method N
6. User approves tests
7. Implement method N
8. Tests pass → move to method N+1
```

**Never skip steps 3, 6.** Never write implementation before tests are approved.

---

## Step 1: The Feature Chain

Before any code, map the full call chain from trigger to data. Check `docs/lookup/` first — most layers already exist.

```
feature: display a song

frontend.load_song(song_id)
  → GET /api/v1/songs/{song_id}             [router: song_updates.py]
  → CatalogService.get_song(song_id)        [service: catalog_service.py]
  → SongRepository.get_by_id(song_id)       [data: song_repository.py]  ← EXISTS
  → CatalogService._hydrate_songs([song])   [service]                   ← EXISTS
  → Song domain model                       [return]

Errors:
  song_id not found       → LookupError → 404
  song_id is None/invalid → 422

New methods needed: none — all layers exist
```

If any layer is missing, name it explicitly. If you're unsure what exists, check `docs/lookup/` before assuming you need to write something new.

Present this chain to the user. **Do not proceed until the chain is approved.**

---

## Required Tests Per Method

Every method needs a test for **every combination of inputs that could behave differently**. No exceptions.

### For any method with ID parameters (song_id, album_id, tag_id, etc.):

| Scenario                                                                              | Required           |
| ------------------------------------------------------------------------------------- | ------------------ |
| All IDs valid, operation succeeds                                                     | ✅                 |
| Primary ID invalid (doesn't exist)                                                    | ✅                 |
| Secondary ID invalid (doesn't exist)                                                  | ✅                 |
| Both IDs invalid                                                                      | ✅                 |
| IDs valid but relationship doesn't exist (e.g. song exists, album exists, not linked) | ✅ (if applicable) |
| IDs valid but relationship already exists (duplicate add)                             | ✅ (if applicable) |
| Any ID is `None`                                                                      | ✅                 |

### For methods that return objects:

- Assert **every field** of the returned object, not just key fields
- Assert **unchanged fields stayed unchanged** (update tests)
- Assert **the effect persisted** via a follow-up read (e.g. `service.get_song(id)`)

### For methods that remove/unlink:

- Assert the link is gone
- Assert the **entity record still exists** (keep-record contract)
- Assert unrelated records are unaffected

### Error cases:

- Assert the **correct exception type** (`LookupError`, `ValueError`, `sqlite3.IntegrityError`)
- Do not test for `Exception` — be specific
- **Always assert state after the error.** Catching the exception is not enough — verify the database is unchanged via a follow-up read. A method that writes then raises will pass the `pytest.raises` block but fail the state check.

```python
# Wrong — only tests that the exception fires
with pytest.raises(LookupError):
    service.create_and_link_album(9999, album_data)

# Correct — also verifies the transaction rolled back
with pytest.raises(LookupError):
    service.create_and_link_album(9999, album_data)
albums = service.search_albums_slim("Ghost Album")
assert len(albums) == 0, "Transaction failed to rollback: album was created despite link failure"
```

---

## Code is Truth

`docs/lookup/` describes intent. The actual code is truth. When they conflict:

1. **Stop.**
2. Report the conflict explicitly: what the doc says, what the code says, what you could not verify (e.g. grep failed, JS file unreadable).
3. Wait for the user to resolve it.

**Never resolve a conflict unilaterally.** Do not restore a method because the doc says it should exist. Do not delete a method because you couldn't find references to it. If you're unsure, say so.

---

## No Silent Fallbacks

**If data is missing or invalid, fail loudly. Never substitute.**

- No year? → `None`. Not `0`, not `1900`, not `datetime.now().year`.
- No song ID? → raise `LookupError`. Not row index, not the first result, not `-1`.
- Empty DB result? → return `None`. Not the previous value, not a default object.
- Foreign key missing? → raise. Not skip, not substitute a related record.

A fallback that makes a test pass is a bug with a green checkmark. The system appears to work while returning wrong data — silently, indefinitely, with no crash and no log.

**Tests must explicitly assert `None` for missing nullable fields.** `assert song.year is None` is a contract. `assert song.year == 0` is certifying a bug.

---

## Rules

**No passive tests.** Every test must assert something. A test that calls a method and asserts nothing is not a test — delete it.

**No raw SQL in service tests.** Verify effects through service methods only. Exception: verifying `IsDeleted=1` for soft-delete tests (no service method exposes that).

**No mocking** repositories, models, or DB connections. Use `populated_db` / `empty_db` / `edge_case_db` fixtures.

**One test per scenario.** Do not test two scenarios in one `def test_...` block.

**Assertion message format:** `assert x == y, f"Expected {y}, got {x}"`

**Test class = one method:**

```python
class TestRemoveSongAlbum:
    def test_valid_link_removes_link(self, populated_db): ...
    def test_invalid_song_id_raises(self, populated_db): ...
    def test_invalid_album_id_raises(self, populated_db): ...
    ...
```

---

## Layer Rules

| Layer      | What to test                                   | Verify effects via        |
| ---------- | ---------------------------------------------- | ------------------------- |
| Repository | SQL correctness, row mapping, NULL handling    | Repo read methods         |
| Service    | Orchestration, business logic, error contracts | Service read methods only |
| API        | Status codes, request/response shape           | TestClient responses      |

Service tests do **not** duplicate repo tests. If the repo is already tested, the service test focuses on the orchestration (hydration, merging, error mapping).

---

## File Placement

**Put code where it belongs, not where it's convenient.**

A stateless utility (string parser, formatter, calculator) does not belong in a service class just because the service happens to call it. It belongs in its own file, imported directly by whatever needs it — service, router, test, doesn't matter.

```python
# Wrong — stuffed into CatalogService because that's nearby
class CatalogService:
    def tokenize_credits(self, text, separators): ...

# Correct — standalone function, imported directly
from src.services.tokenizer import tokenize_credits
```

Tests import the function directly too. No wrapper class, no fixture, no DB setup if none is needed.

---

## Fixture Quick Reference

- `populated_db` — Rich data set. See `conftest.py` header for exact IDs.
- `empty_db` — Schema only. Use for "returns empty" cases.
- `edge_case_db` — NULLs, unicode, orphans, boundary values.

---

## Checklist (run through this before submitting tests for review)

- [ ] Plan was presented and approved before tests were written
- [ ] Every ID parameter has a "missing ID" test
- [ ] Every link operation has a "not linked" test
- [ ] Every add operation has a "duplicate" test (if applicable)
- [ ] No test asserts nothing (passive test)
- [ ] No raw SQL in service tests (except soft-delete IsDeleted check)
- [ ] All returned fields are asserted exhaustively
- [ ] Update tests assert unchanged fields stayed unchanged
- [ ] Remove tests assert the entity record still exists
- [ ] Exception types are specific (`LookupError` not `Exception`)
- [ ] One scenario per test function
