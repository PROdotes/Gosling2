# ExportService Design Document

## Problem Statement
The current save logic in `main_window._on_side_panel_save_requested` mixes:
- **Safety-critical persistence** (write ID3, update DB)
- **UX decisions** (year defaults, orphan prompts, validation feedback)
- **Data transformation** (Yellberus coercion)

This makes it:
- Untestable in isolation
- Blocking (runs in UI thread)
- Hard to modify UX without risking data safety

## Proposed Architecture

### Layer Separation

```
┌─────────────────────────────────────────────────────────────────┐
│                     UI LAYER (main_window / side_panel)         │
│  Responsibilities:                                              │
│  - Stage user edits                                             │
│  - Fetch Song objects from repository                           │
│  - Apply changes with Yellberus coercion                        │
│  - Validate and provide UX feedback (errors, warnings)          │
│  - Handle orphan album prompts                                  │
│  - Build list of "ready-to-save" Song objects                   │
│  - Call ExportService                                           │
│  - Handle results (refresh UI, show errors)                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXPORT SERVICE                              │
│  Responsibilities:                                              │
│  - Receive List[Song] (already modified, validated)             │
│  - Write ID3 tags to each file                                  │
│  - Update DB record for each song                               │
│  - Report success/failure per song                              │
│  - Support progress callbacks (for UI)                          │
│  - Support dry-run mode                                         │
│                                                                 │
│  Does NOT:                                                      │
│  - Fetch songs from DB                                          │
│  - Apply field transformations                                  │
│  - Make UX decisions                                            │
│  - Show message boxes                                           │
│  - Touch status tags (Unprocessed is DB-only, not in ID3)       │
│  - Handle orphan albums (that's Album Editor's job)             │
└─────────────────────────────────────────────────────────────────┘
```

### ExportService Interface

```python
class ExportResult:
    success: bool
    error: Optional[str] = None
    dry_run: bool = False

class BatchExportResult:
    success_count: int
    error_count: int
    errors: List[str]  # Per-file error messages

class ExportService:
    def __init__(self, 
                 metadata_service: MetadataService,
                 library_service: LibraryService):
        ...
    
    def export_song(self, song: Song, dry_run: bool = False) -> ExportResult:
        """Export a single song to ID3 and DB."""
        ...
    
    def export_songs(self, 
                     songs: List[Song], 
                     dry_run: bool = False,
                     progress_callback: Callable = None) -> BatchExportResult:
        """Export multiple songs with optional progress reporting."""
        ...
```

### Order of Operations (Safety)
1. Check file exists and is writable (fail fast)
2. Write ID3 tags
3. IF ID3 succeeds → Update DB
4. IF ID3 fails → Skip DB, report error
5. IF DB fails → Report partial failure (file updated, DB not)

### What ExportService Does NOT Handle

**Status Tags (Unprocessed):**
The `Status:Unprocessed` tag is app-internal only. It lives in the database via `TagRepository`, not in ID3 files. Legacy Gosling 1 wrote status to TKEY/TXXX, but Gosling 2 treats this as DB-only metadata.

**Orphan Albums:**
The orphan album check currently in `main_window._on_side_panel_save_requested` is misplaced. Album lifecycle management belongs in the Album Editor, not the save flow. This code should be removed from main_window.

## UX Improvements (Separate Work)

The following are **not** ExportService concerns, but UI-layer improvements to address later:

| Issue | Where to Fix | How |
|-------|-------------|-----|
| Invalid year silently becomes None | Side Panel validation | Validate before staging, show inline error |
| Empty year defaults to current | Side Panel | Make this a setting (`settings.auto_fill_year`) |
| Orphan album prompt | Main Window | Check if still needed; maybe auto-delete or log instead |

## Migration Path

1. Create `ExportService` with the interface above
2. Create `ExportWorker` (QThread wrapper for async export)
3. Modify `main_window._on_side_panel_save_requested`:
   - Keep: Song fetching, change application, Yellberus coercion, orphan handling
   - Replace: Direct `write_tags`/`update_song` calls → `export_service.export_songs()`
4. Update tests

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/business/services/export_service.py` | Create |
| `src/presentation/workers/export_worker.py` | Create |
| `tests/unit/business/services/test_export_service.py` | Create |
| `tests/unit/presentation/workers/test_export_worker.py` | Create |
| `src/presentation/views/main_window.py` | Modify (use ExportService) |
