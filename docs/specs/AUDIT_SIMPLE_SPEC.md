# Audit System — Design

**Status:** Draft
**Date:** 2026-05-28
**Context:** Full audit trail for forensics. SQLite triggers capture all DB writes automatically. batch_id groups related changes.

---

## Problem

Record what changed, when, and by whom for forensic purposes. Every write to the database must be captured regardless of which code path caused it.

---

## Design

### Database Shape

```sql
CREATE TABLE ChangeLog (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id     TEXT,
    batch_label  TEXT,
    changed_at   TEXT NOT NULL DEFAULT (datetime('now')),
    table_name   TEXT NOT NULL,
    entity_id    INTEGER NOT NULL,
    field_name   TEXT NOT NULL,
    old_value    TEXT,
    new_value    TEXT
);
```

**Columns:**
- `batch_id` — UUID grouping related mutations. NULL until filled in by the write path before commit. A committed NULL is a bug (see Invariants).
- `batch_label` — Short constant identifying the write path: `"ingest"`, `"import"`, `"ui"`, `"undo:<original_batch_id>"`, or a specific op name (`"split_artist"`, etc.). Filled alongside `batch_id`. Lets forensic queries distinguish bulk/programmatic batches from user edits without inferring from row shape.
- `changed_at` — UTC timestamp set automatically by SQLite at insert time. **Per-second granularity** — within a single batch, multiple rows share the same `changed_at`. For chronological order, sort by `id` (AUTOINCREMENT), never by `changed_at`.
- `table_name` — Table that changed: "Songs", "Credits", "Identities", etc.
- `entity_id` — PK of the row that changed.
- `field_name` — Column that changed.
- `old_value` — Before (NULL if insert).
- `new_value` — After (NULL if delete).

**Operation inference:**
- `old_value IS NULL` → insert
- `new_value IS NULL` → delete
- Both NOT NULL → update

---

## Trigger Approach

SQLite DML triggers fire on INSERT, UPDATE, and DELETE on every audited table. Each trigger writes one ChangeLog row per changed field with `batch_id = NULL`.

Empty strings are normalized to NULL:
```sql
INSERT INTO ChangeLog (..., new_value) 
VALUES (..., NULLIF(NEW.col, ''))
```

This ensures operation inference is consistent: both NULL and `''` are treated as "field cleared."

The write path (coordinator, ingestion service, etc.) fills in `batch_id` and `batch_label` before committing:

```sql
UPDATE ChangeLog SET batch_id = :batch_id, batch_label = :batch_label WHERE batch_id IS NULL;
```

On rollback, all trigger-written rows disappear automatically — they are part of the same transaction.

### Why triggers, not Python diff

- Triggers capture intent: INSERT vs UPDATE (IsDeleted 0→1) vs DELETE are distinct operations. A Python diff of two model snapshots cannot distinguish a new entity from a reactivated ghost.
- Triggers capture everything: Credits, Identities, Songs, Publishers — all tables, all write paths, without per-entity Python logic.
- No computed fields: triggers only see real DB columns, not derived properties.

---

## batch_id Flow

Every write path that opens a DB connection must:

1. Generate a `batch_id = str(uuid.uuid4())` before mutations begin.
2. Execute mutations (triggers write NULL rows automatically).
3. Before commit: `UPDATE ChangeLog SET batch_id = :batch_id, batch_label = :label WHERE batch_id IS NULL`
4. Commit.

**Labels per write path** (each path passes a fixed constant):

| Write path                          | Label                       |
|-------------------------------------|-----------------------------|
| `MutationCoordinator.apply()`       | `"ui"`                      |
| `IngestionService.ingest_file()`    | `"ingest"`                  |
| Bulk imports (Jazler, future)       | `"import"`                  |
| Undo path                           | `"undo:<original_batch_id>"`|
| Specific multi-row ops (optional)   | e.g. `"split_artist"`       |

Bulk imports use a single `batch_id` for the entire import.

---

## Invariants

**No committed NULL batch_ids.** A NULL batch_id in the committed ChangeLog means a write path executed outside a properly managed transaction — it generated trigger rows but never ran the fill-in step.

This is a bug indicator, not normal operation. It points directly to the code path that bypasses the mutator.

### NULL Detection

At `BaseRepository.get_connection()`, check for orphaned rows before any new transaction begins. If found, raise an exception immediately:

```python
count = conn.execute("SELECT COUNT(*) FROM ChangeLog WHERE batch_id IS NULL").fetchone()[0]
if count > 0:
    raise RuntimeError(f"Audit integrity broken: {count} orphaned ChangeLog rows detected. A write path is missing batch_id fill-in. Fix and restart.")
```

This prevents the new operation's `flush()` from silently adopting orphaned rows and masking the bug. The exception forces immediate investigation and fix.

**Lifecycle:** this check is intentionally loud and is expected to live in the code for ~1–2 weeks after rollout — long enough to confirm no write path is producing orphans in real use. Once stable, it is removed. It is **not** a permanent production tripwire.

---

## AuditRepository Role

`AuditRepository` handles batch_id fill-in. Single write method, no diffs or logic.

```python
class AuditRepository(BaseRepository):
    def flush_batch(self, batch_id: str, label: str, conn: sqlite3.Connection) -> None:
        conn.execute(
            "UPDATE ChangeLog SET batch_id = ?, batch_label = ? WHERE batch_id IS NULL",
            (batch_id, label)
        )
```

Called by every write path before commit.

---

## Audited Tables

**Every table except `ChangeLog` is audited.** That includes lookup tables (`Types`, `Roles`) and ephemeral ones (`StagingOrigins`) — trigger cost is near-zero and "a Role changed" is exactly the kind of thing forensics wants visible.

`ChangeLog` is not audited (would recurse infinitely).

### Junction Table PKs

`SongAlbums`, `AlbumPublishers`, `RecordingPublishers`, and `MediaSourceTags` have composite PKs (`PRIMARY KEY (col1, col2)`). Add a synthetic auto-increment `ChangeLogID INTEGER PRIMARY KEY` to each so audit can reference rows by a single integer.

The composite key remains for uniqueness; the synthetic ID is audit-only.

---

## Read Use Cases

Three categories of read access. They drive what queries / helper methods `AuditRepository` exposes.

### 1. Per-entity history view ("song X's history")

Surfaced in the UI as a "History" panel on detail views (Song, Identity, Tag, Album, Publisher).

**Rule:** each entity has its own history. Junction events (add/remove) appear in *both* sides' histories. Scalar changes belong only to the entity they happened to — they do **not** propagate transitively.

What's included for an entity X:
- **Direct row changes** — ChangeLog rows where `table_name=<entity table>` and `entity_id=X`.
- **Related junction add/remove** — junction tables where one side references X (e.g. for a song: SongCredits, SongAlbums, RecordingPublishers, MediaSourceTags). Only INSERT/DELETE events count; junction *scalar* changes (e.g. CreditPosition) are not shown.
- **Linked-source row changes** (Songs only) — MediaSources row for the song's SourceID is shown alongside the Songs row, since they're conceptually one entity.

What's **not** included:
- Renames of credited artists, linked tags, parent albums, etc. — those live in the *artist's* / *tag's* / *album's* history, not the song's.
- Junction scalar changes (CreditPosition, TrackNumber, IsPrimary, etc.) — currently excluded; revisit if a use case appears.

**Display:** the audit log stores IDs. When rendering "composer added: NameID 456," the UI shows the *current* display name of 456 (matches the rest of the app). To see what that name used to be, the user clicks through to the artist's history.

Junction-row reconstruction: triggers write one ChangeLog row per column. The full "Freddie removed from song 123 as performer" picture comes from grouping rows by `(table_name, entity_id, batch_id)` and pivoting `field_name`.

### 2. Aggregate / actor patterns

Examples:
- "How often do we tag songs as country" — count INSERTs on MediaSourceTags with `field=TagID, new=<country>`.
- "Which batches were Jazler imports" — filter by `batch_label='import'`.
- "Who keeps tagging songs as country" — deferred until users exist (requires `user_id` column).

`batch_label` is what makes "find me the imports / ingests / undos" answerable without inferring from row shape.

### 3. Undo

The primary motivation for the audit log. Three flavors:

- **Scalar field undo** — `UPDATE <table> SET <field>=<old_value> WHERE <pk>=<entity_id>`. Routed through the mutator so the undo is itself audited. Trivial.
- **Soft-delete undo** — main entities (Songs, Identities, ArtistNames, Albums, Publishers, Tags) have `IsDeleted`. Undo = flip back to 0.
- **Hard-delete undo (junction tables)** — re-INSERT from the row's old_value fields in ChangeLog. Junction rows have integer PKs (see Junction Table PKs); SQLite allows explicit rowid on INSERT, so the original PK can be preserved.

**Batch undo algorithm:**
1. Load all ChangeLog rows for `batch_id=X`.
2. Safety check: reject if any of those entities have been modified by a later batch (would rewrite history under another change).
3. Walk rows in reverse `id` order; reverse each.
4. Route through the mutator. The undo creates a new batch with `batch_label = f"undo:{X}"`.

**Cascading entity undo** — undo of "delete song X" must also restore the cascade-deleted junction rows from the same batch. The `batch_id` grouping makes this clean: undo the whole batch, not just one row.

---

## Open Questions

1. **User context** — Single-user desktop app, no auth. Deferred. No `user_id` column for now. Will be needed for "who tagged this" queries when multi-user lands.
2. **Trigger granularity for UPDATE** — Fire once per row (SQLite default FOR EACH ROW), compare OLD.col vs NEW.col per column. Hand-write triggers per table; drift test (see Success Criteria) catches missing columns.
3. **Test isolation** — Drop triggers in test setup. Audit-specific tests re-enable triggers and verify `batch_id` / `batch_label` fill-in. All other tests run trigger-free.
4. **Bulk import volume** — Jazler import (~50–60k songs) writes one giant batch. Accepted; not addressed further until import lands.

---

## Success Criteria

- [ ] Add synthetic `ChangeLogID INTEGER PRIMARY KEY` to SongAlbums, AlbumPublishers, RecordingPublishers, MediaSourceTags
- [ ] ChangeLog table in schema (with `batch_label`)
- [ ] Triggers written for every table except ChangeLog (INSERT, UPDATE per-column, DELETE; with `NULLIF(NEW.col, '')`)
- [ ] `AuditRepository.flush_batch(batch_id, label, conn)`
- [ ] `MutationCoordinator` calls `flush_batch` with label `"ui"` before commit
- [ ] `IngestionService` calls `flush_batch` with label `"ingest"` before commit
- [ ] NULL detection check in `BaseRepository.get_connection()` (temporary, 1–2 weeks post-rollout)
- [ ] **Drift test** — for every audited table, assert INSERT/UPDATE/DELETE triggers exist and the UPDATE trigger references every column in `PRAGMA table_info`. Catches both missing tables and missing columns.
- [ ] Test: no NULL batch_ids after any operation
- [ ] Test: NULL detected at connection open if previous write path was missing flush()
- [ ] Test: every committed ChangeLog row has a non-null `batch_label`
