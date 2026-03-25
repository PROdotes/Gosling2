# Soft Delete Pivot & Architecture Refactor
**Target Strategy for Next Session**

To resolve the "Split-Brain Restore" problem (where restoring a historical transaction to a hard-deleted anchor generates duplicate or broken reference data), we are migrating the `gosling2` project to a **Soft Delete Architecture**.

This migration requires two distinct workstreams:

## 1. Implement Soft Deletes
The concept of "deletion" now changes from a physical row purge to a visual exclusion.

- **Schema Update**: Introduce an `IsDeleted BOOLEAN DEFAULT 0` column to core entities (`Songs`, `Albums`, `Identities`, `ArtistNames`, `Publishers`, `Tags`).
- **Read Operations**: Every `get_`, `search_`, and `get_all` method across all repositories **must** be updated to include `WHERE IsDeleted = 0`.
- **Delete Operations**: The `delete_X()` repository methods must be rewritten to perform `UPDATE X SET IsDeleted = 1 WHERE ID = ?`.
- **The "Already Exists" Reconnection**: `insert()` methods must be hardened. When attempting to create a new entity (like a Publisher named "Universal Music") that matches a soft-deleted record, the system must perform an `UPSERT` to "wake up" the hidden record (`IsDeleted = 0`) instead of failing a unique constraint or creating a duplicate.

## 2. Refactor Logic to the Service Layer
Enforce the strict **"Smart Service / Dumb Repo"** boundary. 

- **Dumb Repositories**: Repositories must perform strictly raw SQL bindings. We are abandoning the concept of "Intelligent Repositories" that calculate dependency chains (e.g., ripping out complex `get_unlinked_*` logic from the Data Layer).
- **Smart Services**: The `CatalogService` (or new orchestrators) will completely own the authorization and transaction scope.
- **The Foreign Key Blindspot**: **CRITICAL FOCUS.** Because `IsDeleted = 1` is an SQL `UPDATE`, the database's native `FOREIGN KEY` constraints (like `RESTRICT` or `CASCADE`) **will not fire**. 
  - *Example*: Soft-deleting an `ArtistName` will no longer be natively blocked by the database even if 500 `SongCredits` point to it. 
  - *Solution*: The Service Layer *must* execute explicit validation queries ("Does this entity have active links?") before sending the `UPDATE IsDeleted = 1` command to the Repository.

---

### Step 1 for Tomorrow:
Begin with `src/data/schema.py`. Define the new schema fields, run the migrations against the test database, and verify the `empty_db` and `populated_db` fixtures adapt correctly before updating the Repositories.
