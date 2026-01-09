# Today's Focus - January 9, 2026

## 🎯 Remaining Items for v0.1.0
---

### ⚠️ PARTIALLY IMPLEMENTED

#### 3. Advanced Rule Editor (T-82) - ~2.0h
**Backend fully working:**
- `rules.json` exists at `docs/configs/rules.json`
- `renaming_service.py` loads/parses rules dynamically
- Settings dialog shows "✨ Renaming Logic Managed by rules.json" when detected

**Missing:**
- Actual UI editor to add/modify/delete rules in Settings
- Currently read-only notification only

---

### ❌ NOT IMPLEMENTED

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
| Advanced Rule Editor (T-82) | ~2.0h | ⚠️ Partial |
| Filename → Metadata Parser (T-107) | ~2.5h | ❌ Not Started |

**Total Remaining:** ~6.0h
