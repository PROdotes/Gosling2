# Architectural Vision: The Smart Factory & Mutation Protocol

**Date:** 2026-04-22  
**Context:** Solving the "Hydration Hell" and unblocking the Audit/Multi-Edit systems.

---

## 1. The Core Problem: "ID-Based" Friction
Currently, the system is suffering from "Hydration Hell" (10+ hydrations for a single edit) because every layer in the stack is "greedy." 
- The **Router** fetches the song to validate it.
- The **EditService** fetches it again to modify it.
- The **MetadataWriter** fetches it a third time to sync ID3 tags.
- The **Frontend** re-GETs it twice after the 204 response.

This happens because we pass `song_id: int` everywhere. Every function is "blind" and has to "re-read" the entire song from the database to know what it's working on.

## 2. The Solution: The "Smart Factory" (Unit of Work)
We are moving to a **Functional Purity** model where the "Song Editor" becomes a centralized **Orchestrator** (The Factory) that manages the lifecycle of a change.

### The "Transactional Sandwich"
Every mutation (Single or Multi-Edit) follows this strict 2-hydration protocol:
1.  **Hydrate Pre-State**: Fetch the song(s) once to see the "Before" truth.
2.  **Execute Mutation**: Pass the same DB `connection` to the **Dumb Specialists** (Repos/Services) to perform atomic SQL changes.
3.  **Hydrate Post-State**: Fetch the song(s) again using the same connection to see the "After" truth (including path changes).
4.  **Audit**: Compare Pre and Post states and log the diff to the `ChangeLog` table.
5.  **Sync**: Pass the Post-State object directly to the `MetadataWriter` and `FilingService` (0 extra hydrations).
6.  **Commit**: If everything (including the ID3 write) succeeds, commit the transaction.

## 3. The "Mutation Protocol" (Unified Command Pattern)
To support Multi-Edit and simplify the API, we are moving away from 22+ specialized REST endpoints toward a unified **Command Processor**.

### The Payload Structure
The frontend (and internal batchers) will send a standardized mutation object:
```json
{
  "song_ids": [1, 2, 3],
  "scalars": { "bpm": 120, "year": 2025 },
  "add_links": [ { "type": "credit", "id": 5, "role": "Composer" } ],
  "remove_links": [ { "type": "tag", "id": 42 } ]
}
```

### Why this works:
- **Scalars are Sinks**: Title, Year, BPM — you just overwrite the value.
- **Links are Managers**: Credits, Tags, Publishers — you only ever "Add" or "Remove" a link.
- **Idempotent**: "Add Artist 5" does nothing if Artist 5 is already there. No "Toggling" disasters.

## 4. The "Ripping and Tearing" Plan
This refactor is surgical. We will "Dumb Down" the layers from the bottom up.

### Step 1: Dumbing down the Repositories
- Remove "Mini-Factory" logic from `SongRepository.insert` and `reactivate_ghost`.
- Repos go back to being pure SQL executors. They don't know about other repos.

### Step 2: Empowering the Specialists
- Create atomic service workers for `CreditManager`, `TagManager`, and `ScalarSink`.
- These specialists take a `Song` object and a `Connection`, do one thing, and report a status (200/400).

### Step 3: Implementing the Audit Logic
- Use the `AUDIT_REFACTOR_SPEC` to build the `log_update(pre, post)` engine.
- This engine becomes the "Glue" in the Factory loop.

### Step 4: The API Gateway
- The `CatalogRouter` becomes a thin pass-through to the `MutationProcessor`.
- The frontend starts trusting the `200 OK` response body (the Post-State) and stops sending redundant GET requests.

---

## Summary of Success
- **Hydrations**: Dropped from 5-10 down to exactly **2** per transaction.
- **Atomicity**: DB and ID3 tags will finally be in 100% sync (rollback on file error).
- **Auditability**: Every change, no matter how small, is captured in a unified "Undo-ready" log with a Batch UUID.

**Status:** Ready for implementation after morning coffee.
