o,# Groups Logic Status (Dec 21)

## The "Hybrid" State of Unified Artists

As of December 21, the "Unified Artist" (Groups/Aliases) feature is in a transitional state.

### 1. The Strategy
The correct, future-proof way to handle groups is via the Relational Schema:
*   `Contributors` (Artists/Groups)
*   `GroupMembers` (Who belongs to whom)
*   `ContributorAliases` (Alternative names)

### 2. The Legacy Artifact (`S.Groups`)
*   There exists a column `Groups` in the `Songs` table (`S.Groups`).
*   Historically, this was used as a text cache (e.g. "The Beatles; The Who").
*   **Current Status**: This column is **Disabled** in `yellberus.py` (hidden from UI) and **Not Updated** in `SongRepository` (writes are commented out).

### 3. The "Safety Net" Query
The `SongRepository.get_by_unified_artists` method currently queries **BOTH**:
1.  The `S.Groups` column (Legacy/Cache).
2.  The `Contributors` table (Relational Source of Truth).

```sql
WHERE (S.Groups IN (...) OR (C.ContributorName IN (...)))
```

### 4. Directives for Future Agents
*   **DO NOT** re-enable `S.Groups` in `yellberus.py` unless you implement the cache-writing logic in `SongRepository.update`.
*   **DO NOT** remove the `S.Groups` column from the DB schema yet (it's harmless).
*   **FOCUS** on the Relational logic (`ContributorRepository`) as the primary engine.
