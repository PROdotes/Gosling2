---
description: A strict protocol for refactoring or auditing multiple files to prevent agent laziness and hallucinations.
---

# Mass Refactor / Audit Workflow

This workflow is designed to overcome context window limits and "good enough" heuristics by forcing a strict **Survey -> Execute -> Verify** loop.

## Phase 1: Reconnaissance (The Surveyor)
**Goal:** Map the territory before touching it.

1.  **Identify Targets**: Use `find_by_name` (or `grep_search`) to locate all files matching the criteria.
2.  **Create Manifest**: Create a file named `REFACTOR_MANIFEST.md` in `.agent/`.
    *   Content must be a Markdown table or Checklist.
    *   Columns/Fields: `File Path`, `Status` (Pending/Done), `Receipt` (Blank initially).
3.  **Stop**: Do not proceed to code editing in the same turn. ask the user to confirm the scope.

## Phase 2: Execution Loop (The Grinder)
**Goal:** Process files in small batches with strict verification.

1.  **Read Manifest**: Read `REFACTOR_MANIFEST.md` to find the next 3-5 `Pending` files.
2.  **Process Batch**:
    *   For each file:
        1.  `view_file` to read content.
        2.  Perform the Edit (for Refactor) or Analysis (for Audit).
        3.  **Generate Receipt**: Record the specific Line Number and Snippet that was touched.
3.  **Update Manifest**:
    *   Mark the files as `Done`.
    *   Append the "Receipt" data to the manifest (or a separate log if too large).
4.  **Loop Check**:
    *   If `Pending` files remain -> **CONTINUE**.
    *   If all `Done` -> **STOP**.

## Phase 3: Verification (The Gatekeeper)
**Goal:** Ensure the refactor didn't break functionality.

1.  **Spot Check**: Randomly sample 3 modified files and verify the content matches the "Receipt".
2.  **Run Tests**:
    *   If specific unit tests exist for the modified files, run them immediately.
    *   If broad refactor, run the relevant suite (e.g., `pytest tests/unit`).
3.  **Commit**: Only once tests pass, delete the `REFACTOR_MANIFEST.md` (or archive it).

## Critical Rules
*   **[NO_SKIPPING]**: You cannot mark a file `Done` without a Receipt.
*   **[BATCH_SIZE]**: maximum 5 files per turn to prevent context overflow.
*   **[ISOLATION]**: Do not fix unrelated bugs during a mass refactor. Use the "Field Notes" protocol for that.
