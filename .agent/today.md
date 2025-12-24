
# 2025-12-24 - Battle Plan (Night Session)

## 📌 Context
- **Side Panel (T-12) Completed**: Staged changes, Strict Validation, Selection Resilience.
- **Repository Fixed**: `Notes`, `IsActive`, `Publisher`, `Genre` logic corrected.
- **Critical Fix Applied**: `MetadataService.write_tags` FORCED to use `ID3v2.3` and `UTF-16` (encoding=1) to ensure visibility in Windows Explorer.
    - **DO NOT REVERT THIS** unless you want invisible tags.
- **Yellberus**: JSON dependency is DEAD. Python `FieldDef` is Source of Truth for ID3 mappings.

## ✅ Completed Today
- [x] Trace "Notes don't save" bug (Fixed in Repo/Model).
- [x] Trace "Tag Write Failure" (Fixed in MetadataService + Encoding).
- [x] Document Validation Rules (Year, ISRC, Unified).
- [x] Updated TASKS.md (T-12, T-38).

## 🚧 Next Steps
1.  **T-04 Test Consolidation**: The test suite is still fragmented.
2.  **T-06 Legacy Sync**: Album logic refinement.
3.  **T-20 Bulk Edit**: Polishing the Side Panel for multi-selection awareness (already partially working).

## ⚠️ Known Issues / Warnings
- **Composer/Lyricist Union**: `TCOM` tag includes Lyricists. This is intentional (Legacy Logic).
- **ID3 Compatibility**: We are strictly V2.3/UTF-16 now. Usage of V2.4 is banned until further notice.
