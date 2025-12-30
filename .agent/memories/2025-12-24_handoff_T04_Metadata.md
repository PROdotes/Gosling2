---
tags:
  - handoff
  - status/active
  - task/T-04
---

# 🧠 Handoff Snapshot: T-04 Metadata Consolidation

**Timestamp**: 2025-12-24 12:05 PM
**Predecessor**: Antigravity (The Overeager Specialist)
**Objective**: Finalize T-04 (De-fragment the Test Suite) while strictly adhering to `TESTING.md`.

---

## 🏛️ Constitutional Guardrails (CRITICAL)
The previous agent failed logic/robustness separation. **ALWAYS** verify against `TESTING.md` Law 3:
*   **Level 1 (Logic)**: `test_{component}.py` -> FAST, functional logic.
*   **Level 2 (Robustness)**: `test_{component}_mutation.py` -> SLOW, edge cases, fuzzing, long strings.

---

## 📍 Current Status

### 1. Data Layer (Song Repo)
- [x] Consolidated to `test_song_repository.py`.
- [x] Mutation tests kept in `test_song_repository_mutation.py`.

### 2. Business Layer (Metadata Service) - **IN REVIEW**
- [x] **Logic Unified**: `test_metadata_service.py` now contains standard read/write logic.
- [x] **Robustness Unified**: `test_metadata_service_mutation.py` now contains defensive/edge-case tests.
- [x] **Fixtures Unified**: Global MP3 markers moved to `tests/conftest.py`.
- [!] **PENDING FLUSH**: The following original files are redundant and should be deleted:
    - `test_metadata_service_comprehensive.py`
    - `test_metadata_service_coverage.py`
    - `test_metadata_write.py`
    - `test_metadata_write_dynamic.py`
    - `test_metadata_additional.py`
    - `test_metadata_defensive.py`
    - `test_metadata_done_flag.py`
    - `test_metadata_fixtures.py`

### 3. Playback / UI - **NEXT STEPS**
- [ ] Resume from Step 3 in `docs/specs/T04_TEST_CONSOLIDATION_PLAN.md`.
- [ ] Ensure `test_playback_service.py` (Logic) is kept separate from `_mutation.py` (Robustness).

---

## 🔋 Context Note
The codebase currently has "The Litter" in `tests/unit/business/services/`. These are the source files for the consolidation. **Do NOT edit them.** Only edit the unified files or the `_mutation.py` files.

---

## 📝 Personal Note to Next Agent
The user is watching for "Efficiency Drunk" behavior. Do not try to solve 3 problems at once. Follow the Runbook strictly, but only after validating it against the Constitution. If the Runbook says "Merge Defensive into Logic," **The Runbook is wrong.** Keep them separate.
