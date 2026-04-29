# Deepening Opportunities (Post-SongMutator)

**Date:** 2026-04-29  
**Status:** Backlog — prioritized list of architectural improvements  
**Context:** SongMutator (in `docs/specs/song_mutator_seams.md`) establishes the seam-based module pattern. These opportunities build on or address orthogonal friction points.

---

## Overview

The codebase has 13 identified friction points. SongMutator solves or enables solutions for 4-5 of them. The remaining 8-9 require their own seam-based modules. This document lists them in recommended priority order.

**Principle:** Each item becomes a seam (module interface). Data flows in, transformed data flows out. Tests live at seams, not inside implementations.

---

## Priority 1: Extract EditService into Domain-Specific Modules

**Friction Points:** #3 (EditService god object), partially #1, #2 (service initialization)

**Current State:** EditService is 1,185 LOC handling credits, albums, tags, publishers, identity merging, filing, ID3, deletion. No coherent domain boundary.

**Seam Design:**

```
BEFORE (current):
  EditService.add_song_tag(...)
  EditService.remove_song_credit(...)
  EditService.link_album(...)
  ... 20+ methods, all in one class

AFTER:
  CreditManager.add_credit(song_id, credit_id, role_id, conn)
  CreditManager.remove_credit(song_id, credit_id, conn)
  
  AlbumLinker.link_album(song_id, album_id, track_number, conn)
  AlbumLinker.unlink_album(song_id, album_id, conn)
  
  TagManager.add_tag(song_id, tag_id, conn)
  TagManager.remove_tag(song_id, tag_id, conn)
  TagManager.set_primary(song_id, tag_id, conn)
  
  PublisherManager.link_publisher(song_id, publisher_id, conn)
  PublisherManager.unlink_publisher(song_id, publisher_id, conn)
```

**Why This Matters:**
- **Locality:** Credit bugs live in CreditManager. Tag bugs in TagManager. Not scattered across 1,185-line god object.
- **Leverage:** Can reuse "add credit" independently (e.g., from multi-edit or import flows).
- **Testing:** Test CreditManager with song_repo + credit_repo, nothing else. Fast, focused tests.
- **SongMutator integration:** Mutator calls `credit_manager.add_credit()`, `album_linker.link()`, etc. instead of `edit_service.add_song_credit()`.

**Implementation Plan:**
1. Identify manager boundaries (credits, albums, tags, publishers, scalars, identity merging, filing)
2. For each manager: define interface (what callers know)
3. Extract methods from EditService into manager
4. Update SongMutator to call managers instead of EditService
5. Update tests

**Estimated Effort:** Medium (1-2 sprints). High payoff (testability + reusability).

---

## Priority 2: Unify View Model Computation (Eliminate SQL/Python Duplication)

**Friction Point:** #5 (blocker logic duplicated in SQL + Python)

**Current State:** Review blockers computed in two places:
- Python: `compute_review_blockers()` in `src/models/view_models.py`
- SQL: `BLOCKER_SQL` and `NO_BLOCKER_SQL` in `src/data/song_repository.py` lines 15-32

Comment says: "If you add/remove a blocker, update BOTH places." Red flag.

**Seam Design:**

```
OPTION A (Python source of truth):
  BlockerEvaluator.compute_blockers(song: Song) -> List[str]
  
  Called from:
  - view_models: SongView.from_domain() calls evaluator
  - repository: get_song() calls evaluator to set song.blockers field

OPTION B (Query-only):
  Remove BLOCKER_SQL entirely. Fetch songs, compute blockers in Python only.
  Trade: Slightly more DB traffic (don't filter on blockers at query time).
  Gain: Single source of truth.

OPTION C (Database function):
  Move blocker logic to SQL function. Call from both Python and SQL.
  Trade: SQL complexity increases.
  Gain: Source of truth at lowest level.
```

**Recommendation:** Option A (Python source of truth).
- Blocker logic is application domain knowledge, not DB knowledge.
- Easier to understand and test.
- SQL can be optimized later if needed (query with blocker count, not the list).

**Why This Matters:**
- **Locality:** Blocker logic in one place. Change it once.
- **Testing:** Tests specify (song with missing credits, missing albums) → expect specific blockers. No "update both places."
- **Risk reduction:** Currently, a blocker change could diverge between Python and SQL, causing test/prod mismatches.

**Implementation Plan:**
1. Define `BlockerEvaluator.compute_blockers(song) -> List[str]`
2. Update `SongView.from_domain()` to call evaluator
3. Remove BLOCKER_SQL and NO_BLOCKER_SQL from song_repository
4. Update tests to use evaluator
5. Run full test suite

**Estimated Effort:** Low (1-2 days). High payoff (eliminates sync burden).

---

## Priority 3: Centralize Repository Instantiation (Service Factory or DI)

**Friction Points:** #1, #2 (repository redundant instantiation, service init sprawl)

**Current State:** Every service instantiates its own repositories:
```python
# EditService.__init__
self._song_repo = song_repo or SongRepository(db_path)
self._album_repo = album_repo or AlbumRepository(db_path)
# ... 8 more
```

Same pattern in CatalogService, LibraryService, IngestionService. Each instantiation is purely to pass `db_path`—no state.

**Seam Design:**

```
FACTORY INTERFACE:
  class RepositoryFactory:
    def get_song_repo() -> SongRepository
    def get_album_repo() -> AlbumRepository
    def get_credit_repo() -> CreditRepository
    ... (one method per repo type)

USAGE:
  # Before
  edit_service = EditService(db_path)
  
  # After
  factory = RepositoryFactory(db_path)
  edit_service = EditService(factory)
  
  # Inside EditService
  def __init__(self, factory: RepositoryFactory):
      self._song_repo = factory.get_song_repo()
      self._album_repo = factory.get_album_repo()
```

**Benefits:**
- **Locality:** Repo instantiation in one place (factory).
- **Leverage:** All services use the same factory, consistent connection pooling.
- **Testing:** Inject a mock factory with fake repos.
- **Future:** Connection pooling added to factory, benefits all services automatically.

**Alternative:** Full DI container (e.g., Injector library). More powerful, more complex.

**Recommendation:** Start with simple factory. Upgrade to DI if complexity grows.

**Implementation Plan:**
1. Create `RepositoryFactory` class
2. Move all repo instantiation to factory
3. Update services to receive factory (not db_path)
4. Update tests to inject mock factory
5. Remove `db_path` parameter from service constructors

**Estimated Effort:** Medium (1 sprint). Medium payoff (cleaner service boundaries).

---

## Priority 4: Extract Hydration Strategy (Eliminate N+1 Query Risk)

**Friction Points:** #6 (hydration scattered), #11 (identity N+1 queries)

**Current State:** Data is fetched in skeleton form, then "hydrated" (relationships loaded) by services:
- `LibraryService.hydrate_songs()` loads credits, albums, publishers, tags
- `IdentityService._hydrate_identities()` loads aliases, members, groups
- Unclear which queries are needed for a "full" entity
- Risk of N+1 (loading 100 songs = 100 additional queries for relations)

**Seam Design:**

```
HYDRATION STRATEGIES:
  interface HydrationStrategy:
    def hydrate(song_ids: List[int], conn) -> List[Song]

  SkeletonStrategy:
    # Just basic fields (title, bpm, year, isrc)
    def hydrate(...): return songs_with_no_relations

  WithCreditsStrategy:
    # Basic + credits only
    def hydrate(...): return songs_with_credits

  FullStrategy:
    # Basic + credits + albums + tags + publishers
    def hydrate(...): return fully_hydrated_songs

USAGE:
  # In repo
  strategy = FullStrategy()
  songs = strategy.hydrate([1, 2, 3], conn)
  
  # Client knows what they're getting
  songs = repo.get_songs_with(strategy=WithCreditsStrategy())
```

**Why This Matters:**
- **Locality:** Hydration strategies defined in one place. Change query logic once.
- **Performance predictability:** Caller specifies what relations they need, no surprises.
- **Testing:** Mock strategies return test data with known relations.
- **Prevents N+1:** Strategies use single batch queries, not one-per-entity.

**Implementation Plan:**
1. Define `HydrationStrategy` interface
2. Implement strategies for each use case (skeleton, with credits, full, etc.)
3. Update repositories to accept strategy parameter
4. Migrate all hydration calls to use strategies
5. Add tests verifying query counts for each strategy

**Estimated Effort:** Medium-High (1-2 sprints). High payoff (performance + clarity).

---

## Priority 5: Extract Metadata Composition (Implicit Sequencing → Explicit)

**Friction Point:** #12 (metadata service composition implicit in routers)

**Current State:** Three services in parallel:
- `MetadataService`: Extracts from files (reads ID3, etc.)
- `MetadataParser`: Parses extracted frames → domain model
- `MetadataFramesReader`: Manages frame-to-category mappings

Routers know the sequence: call MetadataService, then MetadataParser. No clear contract.

**Seam Design:**

```
COMPOSITOR INTERFACE:
  class MetadataExtractor:
    def extract(file_path: str) -> ExtractedMetadata
    
IMPLEMENTATION:
  def extract(self, file_path: str):
      frames = self._metadata_service.read_file(file_path)
      metadata = self._parser.parse_frames(frames)
      return metadata

USAGE (BEFORE):
  # Router knows the sequence
  frames = metadata_service.read_file(path)
  metadata = metadata_parser.parse(frames)
  return metadata

USAGE (AFTER):
  # Router just calls one interface
  metadata = extractor.extract(path)
  return metadata
```

**Why This Matters:**
- **Locality:** Composition logic in one place (MetadataExtractor). Changes to sequencing/error handling are localized.
- **Leverage:** All routers call one interface, not three services.
- **Testing:** Test extractor's error handling (files missing, parse fails, etc.) once, not in every router test.

**Implementation Plan:**
1. Create `MetadataExtractor` class
2. Move composition logic from routers into extractor
3. Routers call `extractor.extract()` instead of sequencing services
4. Tests verify extractor behavior (happy path, error cases)

**Estimated Effort:** Low (2-3 days). Medium payoff (clarity + reusability).

---

## Priority 6: Consolidate JavaScript State Management (Orchestrator → Event Bus or Store)

**Friction Points:** #8, #9 (JS handler/renderer coupling, orchestrator isolation)

**Current State:** Frontend state is split:
- `main.js` directly dispatches to handlers
- Handlers sometimes call orchestrator functions
- Modals scattered across components
- No clear event flow or state model

**Seam Design:**

```
EVENT BUS INTERFACE:
  class EventBus:
    def emit(event_type: str, data: dict) -> None
    def on(event_type: str, callback: Function) -> None

RENDERERS:
  renderSongEditor() → emits "song:opened", data={song}
  renderTagList() → emits "tag:selected", data={tag_id}

HANDLERS (listeners):
  bus.on("song:opened", handleSongOpened)
  bus.on("tag:selected", handleTagSelected)
  
STATE:
  Store holds current state (selected song, open modals, etc.)
  Handlers dispatch actions → Store updates → re-render

FLOW:
  User clicks → Renderer emits event → Store updates → Handler re-renders
  (No direct handler-to-renderer coupling)
```

**Benefits:**
- **Locality:** Event flow visible in one place (event registry).
- **Leverage:** Renderers and handlers decouple via events. Can swap renderer without changing handler.
- **Testing:** Mock event bus, verify emissions and handlers.

**Implementation Plan:**
1. Design event types (song:opened, credit:added, modal:closed, etc.)
2. Create `EventBus` class (simple pub/sub)
3. Create `Store` class to hold UI state
4. Migrate handlers to emit events instead of calling functions
5. Migrate renderers to listen for events instead of embedding all logic

**Estimated Effort:** High (2-3 sprints, affects all JS). High payoff (testability + maintainability).

---

## Priority 7: Decouple JavaScript Renderer and Handler (HTML Contract → Interface)

**Friction Point:** #8 (renderer/handler coupling via HTML structure)

**Current State:** Renderer builds HTML with data attributes; handler reads them via selectors. No explicit contract.

**Seam Design:**

```
BEFORE (implicit coupling):
  renderSongEditor() {
    return `<input data-action="change-title" value="${song.title}">`
  }
  
  handler() {
    const titleInput = el.querySelector('[data-action="change-title"]')
    titleInput.addEventListener('change', ...)
  }
  // If you rename data-action, handler breaks. No way to know.

AFTER (explicit interface):
  const RENDERER_CONTRACT = {
    titleInput: 'input[data-field="title"]',
    creditsList: 'ul.credits',
    tagChips: '.tags [data-tag-id]'
  }
  
  renderSongEditor() {
    return `<input data-field="title" value="${song.title}">`
  }
  
  handler(elements) {
    // elements = { titleInput, creditsList, tagChips }
    elements.titleInput.addEventListener('change', ...)
  }
  
  // Contract is explicit. If you change HTML, update contract. No silent breaks.
```

**Why This Matters:**
- **Locality:** Contract lives in one place. If HTML structure changes, it's obvious what handlers need updating.
- **Testing:** Can test renderer (does it produce expected structure?) separately from handler (does it wire listeners correctly?).
- **Refactoring:** Rename a selector once, not hunt through 10 handlers.

**Implementation Plan:**
1. Define renderer contracts (selectors for key elements)
2. Update renderers to follow contract (classes, data attributes)
3. Update handlers to accept contract + elements map
4. Add tests: renderer produces contract, handler consumes it

**Estimated Effort:** Medium (1-2 sprints). Medium-High payoff (testability).

---

## Priority 8: Extract Router Boilerplate (Decorators or Middleware Pattern)

**Friction Point:** #7 (30+ endpoints repeating same pattern)

**Current State:** Every mutation endpoint follows the same pattern:
```python
@router.patch("/songs/{id}")
async def update_song(id, request):
    try:
        result = service.update(id, request.data)
        return SongView.from_domain(result)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except LookupError:
        return JSONResponse(status_code=404)
    except Exception:
        return JSONResponse(status_code=500)
```

This pattern repeats 30+ times.

**Seam Design:**

```
OPTION A (Decorator):
  @mutation_endpoint(service_method="update_song_scalars")
  async def update_song_scalars(id, request):
      return request.data  # Decorator handles service call, view conversion, error mapping
  
  # Decorator:
  # 1. Call service method
  # 2. Convert result to view model
  # 3. Map exceptions to HTTP codes
  # 4. Return response

OPTION B (Middleware):
  class MutationHandler:
    def handle(self, request, handler_func):
        try:
            result = handler_func(request)
            return SongView.from_domain(result)
        except ValueError: ...
        except LookupError: ...

OPTION C (SongMutator integration):
  @mutation_endpoint
  async def mutate_song(request):
      command = SongMutationCommand.from_request(request)
      result = mutator.apply(command)
      return SongView.from_domain(result)
  
  # All mutations go through mutator.
  # Boilerplate limited to: parse request → build command → call mutator.
```

**Recommendation:** Option C (once SongMutator is live). Then Option A (decorator for any remaining patterns).

**Why This Matters:**
- **Locality:** Error handling in one place (decorator or middleware).
- **Leverage:** Apply decorator to 30 endpoints once, benefits all.
- **Consistency:** No missing error codes, no duplicate try/except blocks.

**Implementation Plan:**
1. Once SongMutator is live, create thin adapter routers (parse + command building only)
2. If other patterns emerge, build decorator/middleware to eliminate them
3. Tests: Decorator correctly maps exceptions, view conversion works

**Estimated Effort:** Low-Medium (1 sprint after SongMutator). Medium payoff (consistency).

---

## Priority 9: Clarify Ingestion Service State Machine

**Friction Point:** #9 (class-level state, implicit lifecycle)

**Current State:** IngestionService holds class-level state:
```python
class IngestionService:
    _active_tasks: Dict = {}
    _session_success: int = 0
    _session_action: int = 0
```

State persists across CatalogService re-instantiation. Lifecycle tied implicitly to HTTP requests, no cleanup on error.

**Seam Design:**

```
INGESTION SESSION INTERFACE:
  class IngestionSession:
    def __init__(self):
        self.batch_id = uuid4()
        self.success_count = 0
        self.action_count = 0
        self.started_at = now()
    
    def process(self, files: List[File]) -> IngestionResult:
        # Explicit lifecycle
        # Results captured here
        # Cleanup on exit
        
    def cancel(self):
        # Explicit cancellation
        
    def get_status(self) -> IngestionStatus:
        # Query state

USAGE (BEFORE):
  # State implicit, shared
  ingestion_service.process(files)
  session_status = ingestion_service.get_active_tasks()  # Coupled to class state

USAGE (AFTER):
  # State explicit, scoped
  session = IngestionSession()
  result = session.process(files)
  status = session.get_status()  # Scoped to session
```

**Why This Matters:**
- **Locality:** Session state in one place (IngestionSession instance).
- **Testability:** Create session, call process, verify result. No class-level mutation.
- **Lifecycle:** Explicit cleanup (session.close() or context manager).

**Implementation Plan:**
1. Create `IngestionSession` class
2. Move state from class variables to instance variables
3. Update routers to create session instances
4. Update tests to use session instances
5. Add cleanup logic (context manager)

**Estimated Effort:** Low-Medium (1 sprint). High payoff (testability).

---

## Priority 10: Consolidate Configuration (Feature Flags + Validation Rules)

**Friction Point:** #10 (config sprawl, imported everywhere)

**Current State:** All config in one `src/engine/config.py`:
- 20+ boolean flags
- Validation rule dicts
- File extension lists
- Default values

Services import specific items, hiding dependencies.

**Seam Design:**

```
OPTION A (Config object):
  class Config:
    feature_flags: FeatureFlagSet
    validation_rules: ValidationRuleSet
    defaults: DefaultsSet
  
  config = Config.from_env()
  
  service = EditService(config=config)
  
  # Inside service
  if config.feature_flags.AUTO_MOVE_ON_APPROVE:
      ...

OPTION B (Nested modules):
  src/config/
    feature_flags.py
    validation_rules.py
    defaults.py
  
  from src.config import feature_flags, validation_rules
  
  if feature_flags.AUTO_MOVE_ON_APPROVE:
      ...

OPTION C (Environment variables):
  import os
  AUTO_MOVE = os.getenv('AUTO_MOVE_ON_APPROVE', 'true') == 'true'
  
  # Simpler, but less structure.
```

**Recommendation:** Option A (config object). Enables easy testing (inject mock config), dependency visible.

**Why This Matters:**
- **Locality:** Config source in one place. Change defaults, all services see it.
- **Testing:** Mock config object, test with different flags.
- **Visibility:** Services declare config dependencies (in constructor).

**Implementation Plan:**
1. Create `Config` class with nested flag/rule/defaults sets
2. Load from env on startup
3. Pass config to services (constructor injection)
4. Remove scattered imports of individual config items
5. Tests: Inject mock config, verify behavior changes with flags

**Estimated Effort:** Low-Medium (3-5 days). Medium payoff (clarity + testability).

---

## Summary Table

| # | Opportunity | Friction Points | Effort | Payoff | Depends On |
|---|---|---|---|---|---|
| 1 | Extract EditService modules | #3, #1, #2 | Medium | High | SongMutator |
| 2 | Unify blocker logic | #5 | Low | High | — |
| 3 | Repository factory | #1, #2 | Medium | Medium | — |
| 4 | Hydration strategy | #6, #11 | Medium-High | High | — |
| 5 | Metadata composition | #12 | Low | Medium | — |
| 6 | JS state management | #8, #9 | High | High | — |
| 7 | JS renderer/handler | #8 | Medium | Medium | Priority 6 |
| 8 | Router boilerplate | #7 | Low-Medium | Medium | SongMutator |
| 9 | Ingestion state machine | #9 | Low-Medium | High | — |
| 10 | Config consolidation | #10 | Low-Medium | Medium | — |

---

## Sequencing Recommendation

**Phase 1 (Parallel, now):**
- SongMutator (in progress)
- Priority 2: Unify blocker logic (small, independent)
- Priority 10: Config consolidation (enables testing of others)

**Phase 2 (After SongMutator):**
- Priority 1: Extract EditService modules (builds on mutator)
- Priority 3: Repository factory (enables cleaner services)
- Priority 4: Hydration strategy (improves query performance)
- Priority 9: Ingestion state machine (parallel pattern to SongMutator)

**Phase 3 (JavaScript refactor):**
- Priority 6: State management (foundational)
- Priority 7: Renderer/handler (builds on state management)
- Priority 5: Metadata composition (small, independent)
- Priority 8: Router boilerplate (builds on SongMutator)

---

## Notes for Future Explorer

Each opportunity is a **seam** (module interface). When you explore one:

1. **Define the interface first.** What goes in? What comes out?
2. **Identify the seam location.** Where do callers cross into the module?
3. **Check deletion test.** If you deleted this module, would complexity scatter back to N callers? If yes, you've found something deep.
4. **Plan internal seams.** What's private implementation vs what's exposed?
5. **Design tests at seams.** Tests should call the public interface, not internal details.

See `docs/specs/song_mutator_seams.md` for a concrete example of this approach applied to SongMutator.
