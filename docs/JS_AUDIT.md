# JS Code Audit — Issues Found

## Critical / High

| File | Line | Issue | Status |
|------|------|-------|--------|
| `navigation.js` | 71 | `resetIngestStatus()` called on every refresh click — silently nukes counters mid-ingest | **Fixed** — removed `resetIngestStatus()` call from `handleRefreshResults` |
| `main.js` | 473-479 | Switch to ingest mode always resets status regardless of pending count | **Fixed** — guarded reset behind `pendingCount === 0` |
| `main.js` | 297-304 | `updateCachedIngestResult` uses `stagedPath` key but earlier code stored as `path` — cache miss risk | **Fixed** — fallback to `path` match when `stagedPath` is null |
| `ingestion.js` | 640 | Hardcoded style `'[style*="rgba(255, 149, 0"]'` for conflict box — fragile if color changes | **Fixed** — replaced with `data-ghost-box` attribute selector |

## Medium / Fragility

| File | Line | Issue | Status |
|------|------|-------|--------|
| `modals.css` | 407 | Global `.ingest-btn-*` classes without scoping — used in `link_modal.js` | **Fixed** — scoped under `.link-modal .ingest-btn-*` |
| `ingestion.js` | 730-746 | `setupResultsListDelegation` only handles `navigate-search`; resolve-conflict/convert-wav fall through to `SongActionsHandler` — implicit split | **No change** — function doesn't exist; delegation split is already clean via the two-handler pattern |
| `song_actions.js` | 266-269 | References `activeDetailKey` without declaration — closure from main.js scope | **Fixed** — exposed via `ctx.getActiveDetailKey()` method |
| `utils.js` | 74-76 | `renderModuleToolbar` references `ctx.handlers?.filterSidebar` — always undefined | **Fixed** — removed dead reference |

## Low / Code Quality

| File | Line | Issue | Status |
|------|------|-------|--------|
| `song_editor.js` | 189-192, 212, 222, 248, 253 | console.log DEBUG statements in production | **Fixed** — removed 5 debug logs |
| `songs.js` | 108 | TODO: backend sorting — likely stale | **Fixed** — removed stale TODO |
| `orchestrator.js` | 18, 24 | Inline `ctx.getState()` — inconsistent pattern | **Fixed** — reused local `state` variable |
| `filter_sidebar.js` | 51 | `_mode` persists across sessions — could persist bad state | **Fixed** — validates loaded mode is `ALL` or `ANY`, defaults to `ALL` |
| `inline_editor.js` | 113-117 | 100ms blur delay — race condition risk | **Fixed** — replaced `setTimeout(100)` with `requestAnimationFrame` |

## Fixed in This Diff

- `src/services/ingestion_service.py`: `reset_session_status` now checks `_active_tasks` before clearing

## Fixed in JS Audit Pass

- `tests/js/unit/audit_fixes.test.js`: 15 unit tests covering fixes 3, 8, 12, 13
- `main.js`: cleaned 26 unused imports left behind by prior refactors