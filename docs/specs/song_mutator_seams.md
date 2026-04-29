# SongMutator: Seam-Based Architecture

**Date:** 2026-04-29  
**Status:** Reference document for implementation  
**Purpose:** Understand SongMutator as a module with clear seams and internal composition

---

## Overview

SongMutator is a **deep module** that takes JSON-serializable commands and produces Song objects + error codes. Its value comes from collecting transaction logic, sequencing, and side effects behind one clean interface. Inside, it composes other modules at well-defined seams.

**Simple contract:**
```python
# INPUT
command: SongMutationCommand  # JSON-serializable

# PROCESSING
mutator.apply(command)

# OUTPUT
Song (post-state) | raises Exception (400/404/500 mapped by router)
```

---

## The Seams

Each seam is a module interface: data in, data out.

### **Seam 1: Router → Mutator (HTTP → Command)**

**What:** HTTP request becomes structured command.

**Interface:**
```python
# Input
request: HTTP request (JSON body)

# Implementation (in each router adapter)
- Parse request body
- Validate shape (Pydantic model validation)
- Build SongMutationCommand

# Output
command: SongMutationCommand
```

**Adapters (same interface, different sources):**
- `AtomicEditRouter`: Single song edit endpoint → command
- `SpotifyRouter`: Spotify import → command
- `FilenameParserRouter`: Filename pattern + parse result → command
- `MultiEditRouter`: Bulk edit request → command
- `SplitterRouter`: Token resolution + confirms → command
- `PrimaryTagRouter`: Simple {tag_id} → command

Each adapter is thin (just translates external format to internal command shape).

---

### **Seam 2: Mutator Core (Command → Song + DB transaction)**

**What:** The heart. Sequences mutations atomically and captures pre/post state.

**Interface:**
```python
def apply(command: SongMutationCommand) -> Song:
    """
    Apply mutations atomically. Returns post-state of last song.
    
    Args:
        command: Structured mutation request
        
    Returns:
        post-state Song (after all mutations)
        
    Raises:
        ValueError: Invalid command or data not found
        LookupError: Entity not found (404)
        Exception: Other DB errors (500)
    """
```

**Implementation:**
```python
def apply(self, command):
    conn = self._get_connection()  # Transaction owner
    try:
        results = []
        batch_id = uuid4()  # One batch UUID per apply() call
        
        for each song_id in command.song_ids:
            # STEP 1: Capture pre-state
            pre = repo.get_song(song_id, conn)
            if not pre:
                raise LookupError(f"Song {song_id} not found")
            
            # STEP 2: Apply mutations (all via EditService)
            self._apply_scalars(pre.id, command.scalars, conn)
            self._apply_removes(pre.id, command.remove_links, conn)
            self._apply_adds(pre.id, command.add_links, conn)
            if command.set_primary_tag_id:
                self._apply_set_primary(pre.id, command.set_primary_tag_id, conn)
            
            # STEP 3: Capture post-state
            post = repo.get_song(song_id, conn)
            
            # STEP 4: Audit (TODO - will be wired)
            # audit_service.log_update(pre, post, conn, batch_id)
            
            results.append((pre, post))
        
        # STEP 5: Commit transaction (all-or-nothing)
        conn.commit()
        
        # STEP 6: Execute side effects (outside transaction)
        for (pre, post) in results:
            self._sync_id3(post)      # Errors logged, doesn't break transaction
            self._file_if_needed(pre, post)  # Errors logged
        
        return results[-1][1]  # Return post-state of last song
        
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

**Invariants:**
- One transaction per `apply()` call, all-or-nothing
- One `batch_id` per `apply()` call (groups all mutations in one audit batch)
- Pre/post hydration happens inside transaction (ensures consistency)
- Side effects fire outside transaction (errors don't undo mutations)
- If any mutation fails, entire batch rolls back

**Error mapping (router's job):**
- `LookupError` → HTTP 404
- `ValueError` → HTTP 400
- Other exceptions → HTTP 500

---

### **Seam 3: EditService Operations (Mutations within transaction)**

**What:** Atomic mutation operations. Called from SongMutator with a connection.

**Interface:**
```python
# All methods follow this pattern:

def add_song_tag(
    self,
    song_id: int,
    tag_id: int,
    conn: sqlite3.Connection
) -> None:
    """
    Link a tag to a song. Does NOT open/close connection.
    
    Args:
        song_id: Target song
        tag_id: Tag to link
        conn: Active transaction connection (caller owns it)
        
    Raises:
        ValueError: Invalid operation (e.g., already linked)
        LookupError: Tag not found
    """

# Same pattern for:
def remove_song_tag(song_id, tag_id, conn)
def add_song_credit(song_id, credit_id, role_id, conn)
def remove_song_credit(song_id, credit_id, conn)
def add_song_album(song_id, album_id, track_number, disc_number, conn)
def remove_song_album(song_id, album_id, conn)
def update_song_scalars(song_id, scalars_dict, conn)
def set_primary_tag_id(song_id, tag_id, conn)
def add_song_publisher(song_id, publisher_id, conn)
def remove_song_publisher(song_id, publisher_id, conn)
```

**Critical rule:** EditService methods **do not open connections**. They receive `conn` as a required parameter. This allows SongMutator to sequence multiple operations on the same transaction.

**Old pattern (pre-mutator):**
```python
# EditService opened its own connection
def add_song_tag(self, song_id, tag_id):
    conn = self._get_connection()  # Each call opens a connection
    try:
        # ... do work
        conn.commit()
    finally:
        conn.close()
```

**New pattern (mutator era):**
```python
# Caller (SongMutator) owns connection
def add_song_tag(self, song_id, tag_id, conn):
    # ... do work, use provided conn
    # Do not commit/close
```

**Internal details (private to EditService):**
- Resolution logic (get_or_create for missing entities)
- Validation (role exists, tag exists, etc.)
- Auto-promote logic (if removing primary genre, promote next genre)

These are not SongMutator's concern.

---

### **Seam 4: Auditor (Pre & Post States → Audit Log)**

**What:** Diffs two song states and writes audit trail.

**Interface:**
```python
def log_update(
    self,
    pre: Song,
    post: Song,
    conn: sqlite3.Connection,
    batch_id: str
) -> None:
    """
    Log all changes between pre and post state.
    
    Writes to:
    - ChangeLog (field-level: old value → new value for each changed field)
    - ActionLog (high-level: one UPDATE event)
    
    Args:
        pre: Song before mutations
        post: Song after mutations
        conn: Active transaction connection
        batch_id: UUID grouping related operations in one batch
        
    Raises:
        Exception: DB write fails (propagates for rollback)
    """
```

**Implementation steps:**
1. Diff pre vs post (field by field)
2. For each changed field:
   - Normalize values (convert bool → "0"/"1", None → NULL, lists → sorted strings)
   - Create AuditChange entry (table, record_id, field, old, new)
3. For each changed relation (credits, albums, tags, publishers):
   - Detect additions: in post, not in pre → log as NULL → new
   - Detect removals: in pre, not in post → log as old → NULL
   - Detect modifications: same ID, different fields → log field diffs
4. Explode all changes into individual ChangeLog rows (field-level granularity)
5. Write one ActionLog entry (high-level event)
6. All writes use the transaction connection (if this fails, mutator rolls back)

**Called from:** SongMutator, line 89 (TODO placeholder, to be wired)

**Example output for a song with title + artist change:**
```
ChangeLog:
  - table: MediaSources, record_id: 123, field: MediaName, old: "Old Title", new: "New Title"
  - table: SongCredits, record_id: "123-42-1", field: CreditedNameID, old: "42", new: "99"

ActionLog:
  - action_type: UPDATE
  - target_table: Songs
  - target_id: 123
  - details: {"fields_changed": 2, "credits_changed": 1}
  - batch_id: (same UUID)
```

---

### **Seam 5: FilingService (Pre & Post Song → File Move Decision)**

**What:** Determines if a song's file needs to move based on routing changes.

**Interface:**
```python
def move_if_needed(
    self,
    pre: Song,
    post: Song
) -> None:
    """
    Compare routing for pre and post state. Move file if path changed.
    
    Args:
        pre: Song before mutations (for old path calculation)
        post: Song after mutations (for new path calculation)
        
    Raises:
        Nothing. Errors are logged, not propagated. Mutator continues.
    
    Notes:
        - Only executes if post.processing_status == REVIEWED and AUTO_MOVE_ON_APPROVE
        - File move is outside the DB transaction
        - If move fails, song is flagged for manual move (UI shows button)
    """
```

**Implementation:**
1. Call routing engine on pre-state → old_path
2. Call routing engine on post-state → new_path
3. If paths differ:
   - Move file from old_path to new_path
   - If move fails: log error, flag song with error
4. If paths same: no-op

**Called from:** SongMutator, lines 100-101 (side effects loop)

**Example triggers:**
- Album year changes, affecting folder path
- Artist changes, affecting artist folder
- Processing status changes to REVIEWED and AUTO_MOVE_ON_APPROVE is enabled

---

### **Seam 6: ID3 Writer (Song → File Metadata)**

**What:** Writes song metadata to file tags.

**Interface:**
```python
def write_metadata(song: Song) -> None:
    """
    Write song's metadata to ID3 tags.
    
    Args:
        song: Post-state Song with all metadata fields
        
    Raises:
        Nothing. Errors are logged, not propagated. Song flagged out-of-sync.
    
    Notes:
        - Only executes after conn.commit() (outside transaction)
        - If write fails, song is flagged "ID3 out of sync"
        - Manual re-sync available via API
    """
```

**Implementation:**
1. Extract metadata from song object (title, bpm, year, isrc, credits, etc.)
2. Write to file tags (MP3/FLAC/etc. tags)
3. If write fails: log error, flag song, continue

**Called from:** SongMutator, line 96 (side effects loop)

**Why after commit:**
- ID3 is a projection of DB truth, not part of the transaction
- DB is source of record; file tags are a view
- If ID3 write fails, DB mutation succeeds (song is updated, tags are stale)
- Manual resync available to user

---

### **Seam 7: Router → Response (Song → HTTP)**

**What:** Formats song post-state as HTTP response.

**Interface:**
```python
# Input
song: Song (domain object)

# Implementation (in router)
- Convert Song to SongView (Pydantic view model)
- Serialize to JSON
- Return with HTTP 200

# Output
HTTP 200 + JSON response
```

**Example:**
```json
{
  "id": 123,
  "media_name": "Bohemian Rhapsody",
  "bpm": 145,
  "year": 1975,
  "isrc": "GBUM71029604",
  "processing_status": "REVIEWED",
  "credits": [
    {"id": 42, "name": "Freddie Mercury", "role": "Performer"}
  ],
  "tags": [
    {"id": 5, "name": "Rock", "category": "Genre", "is_primary": true}
  ],
  "albums": [
    {"id": 3, "name": "A Night at the Opera", "track_number": 1}
  ],
  "publishers": [
    {"id": 9, "name": "EMI"}
  ]
}
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ HTTP Request (JSON)                                                         │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │
              [SEAM 1: Router Adapter]
              (parse + validate + build command)
                       │
                       ▼
        ┌──────────────────────────────┐
        │ SongMutationCommand (Python) │
        │ {                            │
        │   song_ids: [123],           │
        │   scalars: {...},            │
        │   add_links: [...],          │
        │   remove_links: [...]        │
        │ }                            │
        └──────────────────┬───────────┘
                           │
              [SEAM 2: SongMutator.apply()]
                           │
        ┌──────────────────┴───────────────────────────────────────────┐
        │                                                               │
        ├─ TRANSACTION SCOPE (conn.begin() ... conn.commit()) ────────┐ │
        │ ┌────────────────────────────────────────────────────────┐   │ │
        │ │ For each song_id:                                      │   │ │
        │ │                                                        │   │ │
        │ │  1. PRE-STATE CAPTURE                                 │   │ │
        │ │     pre: Song = repo.get_song(song_id, conn)         │   │ │
        │ │          ↓ (hydrates credits, albums, tags, etc.)    │   │ │
        │ │                                                        │   │ │
        │ │  2. MUTATIONS [SEAM 3: EditService]                  │   │ │
        │ │     for each in scalars:                             │   │ │
        │ │       edit_service.update_scalars(..., conn)         │   │ │
        │ │     for each in remove_links:                        │   │ │
        │ │       edit_service.remove_tag/credit/... (..., conn) │   │ │
        │ │     for each in add_links:                           │   │ │
        │ │       edit_service.add_tag/credit/... (..., conn)    │   │ │
        │ │     if set_primary_tag_id:                           │   │ │
        │ │       edit_service.set_primary_tag_id(..., conn)     │   │ │
        │ │                                                        │   │ │
        │ │  3. POST-STATE CAPTURE                                │   │ │
        │ │     post: Song = repo.get_song(song_id, conn)        │   │ │
        │ │           ↓ (re-hydrates after mutations)            │   │ │
        │ │                                                        │   │ │
        │ │  4. AUDIT LOGGING [SEAM 4: Auditor]                 │   │ │
        │ │     audit_service.log_update(pre, post, conn, batch) │   │ │
        │ │     → ChangeLog rows (field-level diffs)             │   │ │
        │ │     → ActionLog row (high-level event)               │   │ │
        │ │                                                        │   │ │
        │ │  results.append((pre, post))                          │   │ │
        │ │                                                        │   │ │
        │ │ conn.commit()  ← ATOMIC: all-or-nothing              │   │ │
        │ └────────────────────────────────────────────────────────┘   │ │
        │                                                               │ │
        ├─ SIDE-EFFECTS SCOPE (outside transaction) ──────────────────┐ │ │
        │ ┌────────────────────────────────────────────────────────┐   │ │ │
        │ │ For each (pre, post) in results:                      │   │ │ │
        │ │                                                        │   │ │ │
        │ │  try:                                                 │   │ │ │
        │ │    [SEAM 5: FilingService]                           │   │ │ │
        │ │    if post.processing_status == REVIEWED and ...:    │   │ │ │
        │ │      filing_service.move_if_needed(pre, post)        │   │ │ │
        │ │      → File move if routing path changed             │   │ │ │
        │ │  except Exception:                                    │   │ │ │
        │ │    logger.error(...)  ← Don't break, user sees button │   │ │ │
        │ │                                                        │   │ │ │
        │ │  try:                                                 │   │ │ │
        │ │    [SEAM 6: ID3Writer]                               │   │ │ │
        │ │    id3_writer.write_metadata(post)                   │   │ │ │
        │ │    → Write ID3 tags to file                          │   │ │ │
        │ │  except Exception:                                    │   │ │ │
        │ │    logger.error(...)  ← Flag song "out of sync"      │   │ │ │
        │ │                                                        │   │ │ │
        │ └────────────────────────────────────────────────────────┘   │ │ │
        │                                                               │ │ │
        └───────────────────────────────────────────────────────────────┘ │
        │                                                                   │
        └─ return results[-1][1]  (post-state Song) ──────────────────────┘
                           │
                           ▼
                    ┌──────────────────┐
                    │ Song domain obj  │
                    └────────┬─────────┘
                             │
              [SEAM 7: Router Response Formatter]
              (convert to view model + serialize)
                             │
                             ▼
                  ┌────────────────────────┐
                  │ HTTP 200 + JSON        │
                  │ {id, title, credits..} │
                  └────────────────────────┘
```

---

## Why This Is Deep Module Architecture

**Interface (what callers know):**
- One method: `apply(command) -> Song`
- One command shape (scalars, links, primary tag)
- Clear error codes

**Implementation (callers don't need to know):**
- Transaction ownership and lifecycle
- Pre/post hydration
- Sequencing of operations
- Batch audit UUID generation
- Side effects execution order
- Connection pooling (future optimization)
- Audit diffing algorithm
- Filing routing logic

**Leverage (what callers get):**
- 6+ previous entry points (atomic edit, Spotify, filename parser, multi-edit, splitter, primary tag) all call one interface
- Tests write once: `command in, Song out`
- Atomicity guaranteed (no half-committed mutations)
- Audit trail guaranteed (if mutation succeeds, audit writes succeed)

**Locality (what maintainers get):**
- Transaction boundaries in one place
- Sequencing in one place
- Audit integration in one place
- Side effect error handling in one place
- If you need to change "what gets audited," you change one module

**Deletion test:** If you deleted SongMutator, all that transaction+sequencing+audit logic would re-scatter across 6 routers. ✓

---

## Transaction Coordinator Pattern

**Important Design Decision (2026-04-29 evening):**

SongMutator is part of a larger pattern. Don't build a self-contained `SongMutator.apply()` that owns its own connection. Instead, build a **MutationCoordinator** that owns the transaction and delegates to specific mutators.

### Why

Spotify import might need:
1. Song scalars updated (SongMutator)
2. Credits added (CreditMutator, future)
3. Tags added (TagMutator, future)

All must commit atomically in one transaction. If SongMutator owns its connection, each mutation opens/closes separately. Half-commits are possible.

### Architecture

```python
# ROUTER
@router.post("/songs/mutate")
async def mutate(request):
    command = SongMutationCommand.from_request(request)
    result = coordinator.apply(command)  # ← One entry point
    return SongView.from_domain(result)

# COORDINATOR (owns transaction + connection)
class MutationCoordinator:
    def apply(self, command: SongMutationCommand) -> Song:
        conn = self._get_connection()
        batch_id = uuid4()
        
        try:
            # Delegate to specific mutators
            song_post = self._song_mutator.apply_within(
                command,
                conn,
                batch_id
            )
            
            # Future: other mutators
            # tag_post = self._tag_mutator.apply_within(...)
            # credit_post = self._credit_mutator.apply_within(...)
            
            # ONE atomic commit for all mutations + audits
            conn.commit()
            
            # Side effects (outside transaction)
            self._id3_writer.write_metadata(song_post)
            self._filing_service.move_if_needed(pre, song_post)
            
            return song_post
            
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

# SONG MUTATOR (works within transaction)
class SongMutator:
    def apply_within(self, command, conn, batch_id):
        """Apply song mutations. Does NOT own connection or transaction."""
        pre = self._repo.get_song(command.song_ids[0], conn)
        
        # ... apply mutations via EditService
        
        post = self._repo.get_song(command.song_ids[0], conn)
        
        # Audit within same transaction
        self._audit_service.log_update(pre, post, conn, batch_id)
        
        return post
```

### Seam Diagram (Updated)

```
HTTP Request (JSON)
    ↓
[SEAM 1: Router Adapter]
(parse + validate + build command)
    ↓
SongMutationCommand
    ↓
[SEAM 2: MutationCoordinator.apply()]
(owns transaction + connection + routing)
    │
    ├─ [SEAM 2a: SongMutator.apply_within()]
    │  ├─ Pre-hydrate
    │  ├─ Apply mutations (EditService)
    │  ├─ Post-hydrate
    │  └─ [SEAM 4: SongAudit.log_update()] ← inside transaction
    │
    ├─ [SEAM 2b: TagMutator.apply_within()] ← future
    │  └─ [SEAM 4b: TagAudit.log_update()]
    │
    └─ [SEAM 2c: CreditMutator.apply_within()] ← future
       └─ [SEAM 4c: CreditAudit.log_update()]
    │
    ├─ conn.commit() ← ONE atomic commit, all audits persisted
    │
    ├─ [SEAM 5: FilingService.move_if_needed()]
    ├─ [SEAM 6: ID3Writer.write_metadata()]
    │
    └─ return Song post-state
        ↓
    [SEAM 7: Router Response]
        ↓
    HTTP 200 + JSON
```

### For Now (SongMutator Phase)

- Coordinator only calls SongMutator
- SongMutator.apply_within() is the actual implementation
- Future mutators (Tag, Credit, Album, Publisher) follow same pattern
- Each gets its own audit seam (SongAudit, TagAudit, etc.)
- Coordinator handles all the wiring

### Why This Wins

- **One transaction:** All-or-nothing. Coordinator owns it.
- **One batch UUID:** All audits grouped together, even if multiple mutators run.
- **Clean separation:** SongMutator only knows about songs. TagMutator only knows about tags.
- **Easy expansion:** Add CreditMutator later? Add one more `apply_within` call, nothing else changes.
- **Optional mutations:** If command only has song scalars, only SongMutator runs. Others are no-ops.

---

## Implementation Checklist

- [ ] Create `src/services/mutation_coordinator.py`
- [ ] Create `src/services/song_mutator.py` (implements `apply_within()`)
- [ ] Migrate `EditService` methods to accept `conn` parameter (required, no fallback)
- [ ] Wiring: Audit logging (audit_service.log_update inside SongMutator.apply_within)
- [ ] Wiring: Filing service (lines 100-101, after commit)
- [ ] Wiring: ID3 writer (line 96, after commit)
- [ ] Create router adapter (parse request → build command → call coordinator)
- [ ] Migrate frontend to use new command shape
- [ ] Delete old mutation endpoints
- [ ] Tests: Command → Song (happy path, errors) via coordinator
- [ ] Tests: Multi-song atomicity
- [ ] Tests: Side effect error handling (ID3/filing errors don't break transaction)

---

## Next Steps

Once MutationCoordinator + SongMutator are implemented:

1. **Verify atomicity:** Test that failed audit write causes rollback
2. **Verify batch UUID:** Multiple songs get same batch_id
3. **Then design other mutators** (Tag, Credit, Album, Publisher) following same pattern
4. **Then expand coordinator** to route to multiple mutators based on command shape

Each new mutator is isolated—coordinator just adds another `apply_within` call.

---

## File Structure (Future)

```
src/services/
  mutation_coordinator.py    # Owns transaction, routes to mutators
  song_mutator.py            # Song-specific mutations (apply_within)
  tag_mutator.py             # Tag-specific mutations (future)
  credit_mutator.py          # Credit-specific mutations (future)
  album_mutator.py           # Album-specific mutations (future)
  publisher_mutator.py       # Publisher-specific mutations (future)

src/services/audit/
  song_audit.py              # log_update(pre: Song, post: Song, conn, batch_id)
  tag_audit.py               # log_update(pre: Tag, post: Tag, conn, batch_id) (future)
  credit_audit.py            # log_update(pre: Credit, post: Credit, conn, batch_id) (future)
```

Each mutator pairs with its audit. Coordinator glues them together.
