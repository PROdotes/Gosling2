# Today's Focus - January 9, 2026

## 🎯 Remaining Items for v0.1.0

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

### ❌ NOT IMPLEMENTED

#### 3. "Missing Data" Column Filter (T-106) - ~1.5h
When the **Missing Data** filter is active:
- Save the current column layout (order, visibility, width) to a temporary cache.
- Hide all **optional** columns, showing only fields marked `required=True` in Yellberus.
- Disable column‑layout persistence while the filter remains on.
- When the filter is turned off, restore the original column layout and re‑enable saving.

---

#### 4. Filename → Metadata Parser (T-107) - ~2.5h
Parse filename patterns to auto-populate metadata on import:
- Custom pattern definitions (e.g., `{Artist} - {Title}`, `{Track}. {Title}`)
- Fallback when ID3 tags are missing or empty
- UI in Settings to define/test patterns

---

## v0.2+ Items (Correctly Deferred)
- T-28 Leviathans Split (library_widget.py = 2732 lines!)
- T-62 Async Background Save
- MS Access Migration
- T-Tools: Planned "Inventory Management" suite for orphaned entities and global browsing

---

## 📊 Summary
| Task | Estimate | Status |
|------|----------|--------|
| Completeness Indicator (T-104) | ~2.0h | ⚠️ Partial |
| Advanced Rule Editor (T-82) | ~2.0h | ⚠️ Partial |
| "Missing Data" Column Filter (T-106) | ~1.5h | ❌ Not Started |
| Filename → Metadata Parser (T-107) | ~2.5h | ❌ Not Started |

**Total Remaining:** ~8.0h

