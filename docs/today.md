# Today's Focus - January 9, 2026

## ✅ FIXED: Ctrl+F Not Working
**Status: DONE** - `setFocus` proxy was missing in `GlowLineEdit`. Added it.

---

## 📊 Roadmap Deep Dive: Unchecked Features Analysis

### ✅ SHOULD BE MARKED DONE

#### Quick Lookup (T-105) - `Ctrl+F` focuses search box
- [x] Code is in place and verified working.
- [x] **Fix Album Manager Crash**: Resolved NameError in `_on_album_picked_context`.
- [x] **Fix Album Manager Population**: Correctly handle string context data for Create New mode.
- [ ] **T-Tools**: Planned "Inventory Management" suite for v0.2 to handle orphaned entities and global browsing (See `docs/T_TOOLS.md`).

### Known Issues (v0.1)
- [x] **Album Chip Refresh**: Fixed by connecting `data_changed` signal to panel refresh.


#### 4. ZAMP Search Button (T-103) - ~30 min 🔴 Gosling 1 Parity
- [x] Added "ZAMP" to providers list in `side_panel_widget.py`
- [x] Added URL template logic.

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

#### 3. "Show Truncated" Filter (T-102) - ✅ DONE
**Implemented:**
- ✅ Split `is_complete()` (for filters) vs `is_valid()` (for save validation)
- ✅ "Missing Data" filter shows songs missing REQUIRED fields only
- ✅ "Ready to Finalize" filter shows complete songs with Unprocessed tag
- ✅ Filter labels updated: "Pending" → "Ready to Finalize", "Incomplete" → "Missing Data"
- ✅ Publisher split: Song-level (required) vs Album-level (informational)
- ✅ `performers` is now strictly required
- ✅ `groups` field deprecated (hidden, non-portable)

---

### ❌ NOT IMPLEMENTED

#### 6. "Missing Data" Filter Column Restriction (T-??) - 🛠️
When the **Missing Data** filter is active:
- Save the current column layout (order, visibility, width) to a temporary cache.
- Hide all **optional** columns, showing only fields marked `required=True` in Yellberus.
- Disable column‑layout persistence while the filter remains on.
- When the filter is turned off, restore the original column layout and re‑enable saving.

---

---

## v0.2+ Items (Correctly Deferred)
- T-28 Leviathans Split (library_widget.py = 2732 lines!)
- T-62 Async Background Save
- MS Access Migration

---

## Notes
- Ctrl+F focus_search code path: `Shortcut → library_widget.focus_search() → emit signal → lambda focuses title_bar.search_box`
- May need to check if search_box exists and is visible when focus is requested
