# Logging Improvements

## Problem
Application logs trace what happened but not why. Symptoms:
- A single UI action triggers 10 hydrations — logs show the calls but not the originating action.
- Manual edits (credits, publisher, album, ISRC) leave no trace — only the initial ingest ID3 data is logged.
- When something breaks, you have to read the code to reconstruct the call chain.
- Double hydrations are visible in the log but untraceable — all entries look identical, no way to know what triggered each one.
- Exceptions in MutationCoordinator are swallowed silently (rollback happens, nothing is logged).
- Coordinator and mutator layers have no entry/exit logs at all — they are invisible in the log tree.

## What's needed

### 1. Request ID via ContextVar
Thread a short request ID (e.g. `req_a3f2`) through every log line without touching any method signatures.

- Set a `contextvars.ContextVar` in a FastAPI middleware at the start of each request.
- The logger formatter reads the context var and prepends the ID to every line.
- Result: all log lines for one request share a prefix. Two identical `get_song` calls are immediately distinguishable — same request ID means double-call within one request, different IDs means separate triggers.
- No service or repo method signatures change.

### 2. Complete entry/exit coverage
Every service method and repository method must have:
- `->` entry log (method name + key args)
- `<-` clean exit log (result summary or rowcount)
- `<- ERROR` or `<- NOT_FOUND` on every premature return or exception path

Currently missing coverage (known gaps):
- `MutationCoordinator.apply()` — no entry, no exit, no error log
- `MutationCoordinator._route()` — silent
- `CreditMutator.apply_within()` / `_update()` / `_add()` / `_remove()` — all silent
- All other mutators (AlbumMutator, TagMutator, PublisherMutator, SongMutator, DeleteMutator) — likely same
- Any `except` block that re-raises without logging
- Any early `return` that exits without a `<-` line

An audit pass is needed across all files in `src/services/` and `src/data/` to find every method that is missing one of these three log points.

### 3. Write operation logging
Service layer should log every data mutation at INFO level:
- What changed (field, old value, new value)
- Which song/entity
- Example: `[EditService] <- update_credits(song_id=223) added Performer 'z++'`

### 4. Exception logging in coordinator
`MutationCoordinator.apply()` must log the exception before re-raising:
```python
except Exception as e:
    logger.error(f"[MutationCoordinator] apply() FAILED: {e}", exc_info=True)
    conn.rollback()
    raise
```

## Scope
Separate from the audit refactor (docs/specs/AUDIT_REFACTOR_SPEC.md), which is about transactional audit trails in the DB. This is about making gosling.log useful for debugging without reading the code.

## Implementation order
1. ContextVar middleware + formatter change (no logic risk, purely additive)
2. Audit all services and repos for missing entry/exit/error log points, fix gaps
3. Add exception logging to MutationCoordinator
4. Write operation logging at INFO level
