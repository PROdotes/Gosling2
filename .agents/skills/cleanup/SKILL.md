# GOSLING2: Code Hygiene and Deduplication Skill

A skill for performing "Cleanup Passes" on the GOSLING2 codebase to maintain architectural integrity, remove redundant code, and simplify logic.

## 1. Principles
- **No Refactor Without Spec**: All cleanup passes must start with a findings document and a spec.
- **Deduplication Priority**: Focus on Repositories and Services. Extract shared SQL building or business logic into shared helper classes or base repositories.
- **No Method Bloat**: Avoid adding `get_by_id` and `get_by_ids` as separate, duplicated logic paths. Use shared internal query builders or parameters (lists).
- **Simplification**: Replace complex, nested conditionals with descriptive early returns or strategy patterns.
- **Zombie Management**: Any code that has no calls or references MUST be purged immediately.
- **Lookup Alignment**: The `docs/lookup/` files are the "truth". Any cleanup must ensure they stay accurate.

## 2. Techniques
- **Cross-Repository Audit**: Compare `SongRepository`, `AlbumRepository`, and `ArtistRepository`. Look for identical patterns in `_row_to_entity` or boilerplate CRUD methods.
- **Mapping Logic**: Ensure that mapping between DB rows and Pydantic entities is handled in a single, definitive place.
- **Logger Instrumentation**: Ensure all new/refactored methods have ubiquitous logging as per `AGENTS.md`.

## 3. Tool Workflow
- Use `grep_search` to find duplicate string literals or method signatures across files.
- Use `list_dir` to find orphaned files (e.g., test files for removed features).
- Use `docs/lookup/` to verify that all methods listed there are actually implemented.

## 4. Done Protocol
A cleanup is never done without:
1. `black .`, `ruff check . --fix`, `pyright` pass.
2. `pytest` passes 100%.
3. `pytest --cov` coverage is at 100% for the refactored code.
4. `docs/lookup/` is perfect.
