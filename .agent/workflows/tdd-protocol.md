---
description: Test-Driven Bug Fixing Protocol (Junie-mode)
---
// turbo-all
When the user says "Junie-mode this" or asks for a test-driven fix:

1. **Phase 1: Reproduce**
   - Identify the specific incorrect behavior.
   - Create a standalone reproduction script or a new test in `tests/repro/` that fails because of this behavior.
   - Run the reproduction tool (e.g., `pytest tests/repro/test_name.py`) and confirm a "Red" status (failure).

2. **Phase 2: Investigate**
   - Use `grep_search` and `view_file` to trace the execution flow.
   - If necessary, add temporary `print()` or `logging` statements to the codebase to inspect state.

3. **Phase 3: Fix**
   - Apply the fix to the relevant files using `replace_file_content` or `multi_replace_file_content`.

4. **Phase 4: Verify**
   - Run the reproduction script again to confirm it is now "Green" (passes).
   - Run the project's full test suite to ensure no regressions were introduced.

5. **Phase 5: Cleanup**
   - Remove the temporary reproduction script and any debug prints added during Phase 2.
