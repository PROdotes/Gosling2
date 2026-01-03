# T-XX: Parallel I/O for Import & Save Operations

## Problem
Current implementation uses sequential processing for file I/O operations:
- **Import**: Single `QThread` processes files one-by-one
- **Save**: Synchronous `write_tags()` calls in UI thread (blocks UI)

For small batches (1-10 files), this is fine. For larger operations or slow storage (HDD/NAS), it causes:
- Long wait times (100 files @ 100ms = 10+ seconds)
- UI freeze during multi-file saves

## Proposed Architecture

### Producer-Consumer Pattern
```
┌─────────────────────────────────────────────────────────────┐
│   PARALLEL WORKERS (ThreadPoolExecutor, N workers)         │
│   - Read MP3 from disk                                      │
│   - Parse metadata (Mutagen)                                │
│   - Compute audio hash (if enabled)                         │
│                           ↓                                 │
│                    Thread-safe Queue                        │
│                           ↓                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│   SEQUENTIAL WRITER (1 thread)                              │
│   - SQLite INSERT/UPDATE                                    │
│   - Emit progress signals                                   │
└─────────────────────────────────────────────────────────────┘
```

### For Save Operations
- Move `write_tags()` to background worker
- Emit progress signal per file
- Show non-blocking progress toast/bar

## Storage Considerations
| Storage Type | Random I/O | Parallel Benefit |
|-------------|------------|------------------|
| NVMe SSD    | ~0.1ms     | High             |
| SATA SSD    | ~0.5ms     | Medium           |
| HDD 7200rpm | ~10ms      | Low (seek-bound) |
| NAS/Network | ~10-50ms   | High (hides latency) |

## Settings
- `settings.parallel_import_workers` (default: 4, or auto-detect CPU cores)
- `settings.use_parallel_import` (default: False, user-enabled for NAS)

## Priority
**Medium** - Nice-to-have for power users with large libraries or NAS storage.

## Affected Files
- `src/presentation/workers/import_worker.py`
- `src/presentation/views/main_window.py` (save logic)
- `src/business/services/import_service.py`

## Notes
- Audio hash computation is the biggest time sink - consider making it lazy/optional
- SQLite writes must remain sequential (single writer)
- Could use `concurrent.futures.ThreadPoolExecutor` for simplicity
