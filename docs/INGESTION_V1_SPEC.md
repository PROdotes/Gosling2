# INGESTION V1 - Batch & Storage Specification

## Context
The write path now supports Bulk Ingestion (multi-file drops) and Server-side Folder Scanning. However, these features currently cause disk bloat by creating redundant copies in the `STAGING_DIR` and failing to relocate files to their permanent homes.

## 1. File Location & Ownership Policy

The system must distinguish between **Managed Files** (uploaded) and **External Links** (scanned).

### GOSLING_LIBRARY_ROOT (`Z:\Songs`)
This is the "Source of Truth" for the library. 

| Input Method | Strategy | Final DB `SourcePath` | Cleanup Action |
|---|---|---|---|
| **Browser Upload** | **MOVE** | `{LIBRARY_ROOT}/ingested/{id}_{name}` | Delete from Staging |
| **Path Check / Scan** | **LINK** | Original Path (if outside Staging) | No deletion of original |
| **Path Check / Scan** | **STAGED** | `{LIBRARY_ROOT}/ingested/{id}_{name}` | Move from Staging to Library |

### The "No-Copy" Rule for Server Scans
- If `IngestRouter.scan_folder` finds files already on the server, it MUST NOT copy them to `STAGING_DIR`. 
- It passes the original paths directly to `CatalogService.ingest_batch`.

## 2. Service Layer: `ingest_file(path)` Refinement

The `ingest_file` method is the final arbiter of file relocation.

1. **Transaction Phase**:
   - Run `check_ingestion`.
   - If `ALREADY_EXISTS` or `ERROR` -> **Purge** if and only if path is in `STAGING_DIR`. Return.
   - If `NEW` -> Insert into DB using the *current* path as a placeholder.

2. **Commit Phase**:
   - `conn.commit()`.
   - **Relocation**: If the file is currently in `STAGING_DIR`:
     - Move it to `${LIBRARY_ROOT}/ingested/${id}_${filename}`.
     - Update the DB record's `SourcePath` to the new location.
   - If the file is *already* in a permanent location (detected by path prefix), do nothing.

## 3. Router Layer: `scan_folder` & `upload`

- **`POST /api/v1/ingest/upload`**: Continues to save to `STAGING_DIR`. Relocation is handled by the Service.
- **`POST /api/v1/ingest/scan-folder`**: MUST NOT use `shutil.copy`. It simply collects absolute paths and hands them to the Service.

## 4. Safety: Protected Paths
`CatalogService.delete_song` and failure cleanups must NEVER `os.remove()` a file that is not inside `STAGING_DIR` or the explicitly managed `{LIBRARY_ROOT}/ingested/` folder, unless the user explicitly authorizes a "Delete from Disk" action (Next Phase).

---

## Files to Update

| File | Change |
|---|---|
| `src/services/catalog_service.py` | Implement `_relocate_file` logic in `ingest_file`. |
| `src/engine/routers/ingest.py` | Remove `shutil.copy` from `scan_folder`. |
| `src/engine/config.py` | Ensure `get_library_root()` is utilized. |
