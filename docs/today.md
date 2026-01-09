# Today's Focus - January 9, 2026

## 🎯 Remaining Items for v0.1.0

### ✅ IMPLEMENTED (Verified)

#### 1. Completeness Indicator (T-104)
**Traffic Light System Implemented:**
- **Status Deck (Column 0)** now indicates logical health.
- 🔴 **Red (Invalid)**: Missing required fields (overrides everything).
- 🥬 **Cyan/Tele-Green (Unprocessed)**: Valid data, but tagged "Unprocessed".
- 🟠 **Amber (Ready)**: Valid + Processed.
- Logic resides in `Yellberus` and uses standard `LibraryWidget` checks.

---

### ⚠️ PARTIALLY IMPLEMENTED

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
- Save the current column layout.
- Hide all **optional** columns, showing only fields marked `required=True`.
- Disable persistence.
- Restore layout when disabled.

---

#### 4. Filename → Metadata Parser (T-107) - ~2.5h
Parse filename patterns to auto-populate metadata on import:
- Custom pattern definitions (e.g., `{Artist} - {Title}`).
- Fallback when ID3 tags are missing.
- UI in Settings to define patterns.

---

## v0.2+ Items (Correctly Deferred)
- T-28 Leviathans Split
- T-62 Async Background Save
- MS Access Migration
- T-Tools: "Inventory Management" suite

---

## 📊 Summary
| Task | Estimate | Status |
|------|----------|--------|
| **Completeness Indicator (T-104)** | ~2.0h | ✅ Done |
| Advanced Rule Editor (T-82) | ~2.0h | ⚠️ Partial |
| "Missing Data" Column Filter (T-106) | ~1.5h | ❌ Not Started |
| Filename → Metadata Parser (T-107) | ~2.5h | ❌ Not Started |

**Total Remaining:** ~6.0h
