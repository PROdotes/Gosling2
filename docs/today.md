# Today's Focus - January 9, 2026

## 🐛 BUG: Ctrl+F Not Working
**Priority: HIGH** - Quick Lookup shortcut isn't focusing the search box.

**Code exists but may be broken:**
- `main_window.py` line 422-426: Shortcut is wired up
- `library_widget.py` line 2176-2179: `focus_search()` emits signal
- Signal connected at line 399: `self.library_widget.focus_search_requested.connect(lambda: self.title_bar.search_box.setFocus())`

**To investigate:**
1. Is the signal being emitted? (Add debug print in `focus_search()`)
2. Is `self.title_bar.search_box` the correct reference?
3. Is focus being stolen by the table view?

---

## 📊 Roadmap Deep Dive: Unchecked Features Analysis

### ✅ SHOULD BE MARKED DONE (if Ctrl+F bug is fixed)

#### Quick Lookup (T-105) - `Ctrl+F` focuses search box
- Code is in place, but currently not working (bug above)
- Once fixed, mark as `[x]` in roadmap

---

### ⚠️ PARTIALLY IMPLEMENTED

#### 1. Completeness Indicator (T-104) - ~2.0h remaining
**Infrastructure exists:**
- `_get_incomplete_fields()` uses `yellberus.validate_row()`
- Completeness calculated for every row during load
- Used to gate "Done" toggle + validation errors

**Missing:**
- Dedicated visual column with LED/icon showing completeness
- Currently only expressed via disabled buttons and error messages

---

#### 2. Advanced Rule Editor (T-82) - ~2.0h
**Backend fully working:**
- `rules.json` exists at `docs/configs/rules.json`
- `renaming_service.py` loads/parses rules dynamically
- Settings dialog shows "✨ Renaming Logic Managed by rules.json" when detected

**Missing:**
- Actual UI editor to add/modify/delete rules in Settings
- Currently read-only notification only

---

#### 3. "Show Truncated" Filter (T-102) - ~2.0h 🔴 Gosling 1 Parity
**Filtering mechanism supports this:**
- `_show_incomplete` flag exists
- `_get_incomplete_fields()` identifies validation failures
- INCOMPLETE status filtering works in proxy model

**Missing:**
- Dedicated filter tree node or toggle for "Show Truncated"
- Currently is_done filter shows INCOMPLETE but that's Status tag based, not Composer/Publisher specific

---

### ❌ NOT IMPLEMENTED

#### 4. ZAMP Search Button (T-103) - ~30 min 🔴 Gosling 1 Parity
**Quick win!**

Current providers: `["Google", "Spotify", "YouTube", "MusicBrainz", "Discogs"]`

**To implement:**
1. Add "ZAMP" to providers list in `side_panel_widget.py` line 2208
2. Add URL template in `_get_search_url()` around line 2302:
```python
elif provider == "ZAMP":
    return f"https://www.zamp.hr/pretraga?q={q_clean}"
```

---

#### 5. Inline Edit (T-03) - ~2.0h (Major work)
Grid is explicitly read-only:
- `setEditTriggers(NoEditTriggers)` on table
- All items have `setEditable(False)`
- Requires delegate changes and edit commit logic

---

## 📋 Priority Order for Today/This Week

| # | Task | Time | Impact |
|---|------|------|--------|
| 1 | 🐛 Fix Ctrl+F bug | 15min | Unblocks T-105 |
| 2 | ZAMP Search (T-103) | 30min | Quick win, Gosling 1 parity |
| 3 | Show Truncated Filter (T-102) | 2h | Gosling 1 parity |
| 4 | Completeness Indicator (T-104) | 2h | Visual improvement |
| 5 | Rule Editor UI (T-82) | 2h | Power user feature |
| 6 | Inline Edit (T-03) | 2h+ | Nice to have |

---

## v0.2+ Items (Correctly Deferred)
- T-28 Leviathans Split (library_widget.py = 2732 lines!)
- T-62 Async Background Save
- MS Access Migration

---

## Notes
- Ctrl+F focus_search code path: `Shortcut → library_widget.focus_search() → emit signal → lambda focuses title_bar.search_box`
- May need to check if search_box exists and is visible when focus is requested
