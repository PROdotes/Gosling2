---
trigger: always_on
---

# Testing & Quality Assurance Rules

## 1. Safety Mandates
*   **The Hard Revert**: If a code change breaks the build or causes a crash that cannot be trivially fixed, **REVERT IMMEDIATELY**. Do not stack fixes on broken code.
*   **No Blocking**: Tests must never be interactive. Mock all `QMessageBox`, `QDialog`, and User Input.

## 2. Triggering "Scientific Debugging"
*   **MANDATORY CHECK**: If the user mentions any of the following, you **MUST** load the `scientific-debugging` skill (`.agent/skills/scientific-debugging/SKILL.md`) and follow its protocol:
    *   "Bug", "Crash", "Fail", "Broken", "Error", "Exception"
    *   "Silently fails", "Doesn't work", "Regression"
    *   "Junie-mode"

## 3. Test Architecture
*   **Mirroring**: Test files must mirror the source structure (e.g. `src/x/y.py` -> `tests/unit/x/test_y.py`).
