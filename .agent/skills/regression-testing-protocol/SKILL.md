
---
name: Regression Testing Protocol
description: Directives for preventing regression, distinguishing Laws from Tests, and enforcing test coverage for every bug fix.
---

# Regression Testing Protocol

## 1. The "Fix = Test" Mandate
*   **Rule**: You are PROHIBITED from marking a bug fix as "Complete" until you have added a test that reproduces the bug and verifies the fix.
*   **Zero Exemptions**: "It's a simple CSS fix" is not an excuse. If you can't test it, you must justify why.

## 2. Laws vs. Tests
You must decide where your test belongs:

### A. The Immutable Laws (`tests/laws/`)
*   **Criteria**: Use this for **Business Invariants** or **Critical User Flows** that should *never* change (e.g., "Members must merge, not duplicate", "Unlinking splits identity").
*   **The Pact**: Tests in this folder are **Sacred**.
    *   **DO NOT EDIT** existing Law tests to make them pass.
    *   If a Law fails, it means your Application Code is broken. Revert and Rethink.
*   **Format**: `tests/laws/test_law_NNN_description.py`

### B. Standard Regression (`tests/regression/` or `tests/unit/`)
*   **Criteria**: Use this for implementation-specific bugs (e.g., "Function X crashes on None input").
*   **Mutability**: These tests can be updated if the underlying architecture changes.

## 3. The Workflow
1.  **Check the Laws**: BEFORE applying any fix, run `pytest tests/laws/`.
    *   If any Law fails *before* you start, report it immediately.
2.  **Reproduce**: Write your test case (Law or Unit). Assert it Fails (Red).
3.  **Fix**: Apply your code changes.
4.  **Verify**: Run the test. Assert it Passes (Green).
5.  **Regress**: Run `pytest tests/laws/` again to ensure you didn't break anything else.

## 4. Anti-Patterns (Forbidden)
*   **The "Lazy Fix"**: Editing a test assertion because the output changed. **VERIFY** if the change is correct first.
*   **The "Blind Commit"**: Committing code without running the full Law Suite.
