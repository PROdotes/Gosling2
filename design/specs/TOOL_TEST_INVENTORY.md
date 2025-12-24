---
tags:
  - tool/spec
  - status/proposed
  - priority/medium
---

# 🛠️ Specification: Test Inventory Enforcer

**Goal**: Automate "The Law of Inventory" (Law 8 in `TESTING.md`).
**Why**: Prevent "Test Drift" where new features are added without corresponding tests.
**Target Script**: `tools/audit_test_coverage.py` (or rename to `tools/enforce_tests.py`).

---

## 1. The Rules of Engagement

The tool must run in CI/CD (or pre-commit) and return **Exit Code 1** if any of the following rules are violated.

### Rule A: The Mirror Rule (Parity)
Every Python file in `src/` (excluding exceptions) **MUST** have a corresponding test file in `tests/unit/`.

*   **Source**: `src/business/services/metadata_service.py`
*   **Required**: `tests/unit/business/services/test_metadata_service.py`

**Exceptions** (Ignored via config):
*   `__init__.py`
*   `main.py` / `app.py` (Entry points)
*   pure data containers (dataclasses) if tested transitively (though discouraged).

### Rule B: The Coverage Threshold
If a file exists, its coverage must meet the strict standard.

*   **Logic (Default)**: **80%**
*   **Critical (Core)**: **90%** (e.g., `yellberus.py`)
*   **UI (Presentation)**: **70%** (Allowed to be lower due to Qt difficulty, IF Logic is separated).

### Rule C: The "Mutation" Trigger (Law 7)
The tool must parse the AST of the source file.
If the source file imports **System libraries** (`os`, `shutil`, `sys`, `subprocess`) or **mutates state** (`sqlite3` write):
*   **Required**: `tests/unit/.../test_{name}_mutation.py`
*   **Why**: Logic tests aren't enough for I/O bounds.

---

## 2. Configuration (`.test_audit_config`)

Use a JSON or YAML config to manage exemptions. Do NOT hardcode them in the script.

```json
{
  "ignore_files": [
    "src/app.py",
    "src/data/db_migrations.py"
  ],
  "threshold_overrides": {
    "src/presentation/widgets/complex_graph.py": 60
  }
}
```

## 3. Output Format (The "Hit List")

If rules are broken, output a clear, actionable Hit List:

```text
🛑 TEST INVENTORY FAILURE 🛑

MISSING TEST FILES:
[ ] src/business/new_feature.py (Expected: tests/unit/business/test_new_feature.py)

COVERAGE VIOLATIONS:
[ ] src/core/yellberus.py: 78% (Required: 90%) - CRITICAL
[ ] src/utils/parser.py: 12% (Required: 80%)

MUTATION TESTS REQUIRED (Law 7):
[ ] src/data/file_system.py (Imports: shutil, os) -> Missing test_file_system_mutation.py

Fix these errors to pass the build.
```

## 4. Implementation Plan

1.  **Refactor** existing `tools/audit_test_coverage.py`.
2.  **Add AST Parsing**: To detect `import os` etc. for Rule C.
3.  **Add Config Loader**: To read exemptions.
4.  **Add CI Mode**: `--strict` flag that enables the Exit Code 1 behavior.
