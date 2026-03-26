---
description: Code Hygiene and Deduplication Pass
---

When asked to perform a "cleanup", "refactor pass", or "deduplication", follow these steps:

## Phase 1: Audit & Pattern Identification
1. **Systematic Scan**: 
   - Search for structural duplication across all `repositories/`.
   - Search for redundant logic in `services/`.
   - Audit `docs/lookup/` for discrepancies with current implementation.
2. **Identification of Redundancy**:
   - For every new method proposal, check if an existing similar method can be DRYed (e.g., merging `get_by_id` and `get_by_ids` into a single logical path).
3. **Finding Documentation**:
   - Create a findings document: `docs/findings/[YYYYMMDD]_cleanup_audit.md`.
   - Link all identified duplicates OR "smelly" code (overly complex logic).
   - For every duplication, propose a DRY-er abstraction.
4. **Draft Specification**:
   - Write a formal Refactor Spec in `docs/refactors/`. 
   - Define the concrete "Before" and "After" state for at least one critical example.
5. **STOP**: Present the audit findings and the refactor spec to the user.

## Phase 2: Authorization
1. Wait for user approval of the Refactor Spec.
2. If given a "GO", proceed to implement one atomic improvement at a time.

## Phase 3: Execution (via /writing)
1. For each item in the approved spec, invoke the `/writing` workflow.
2. **STRICTLY** one method at a time: 
   - 1. Test
   - 2. Implementation
   - 3. Verify
3. **DIFF FIRST**: After writing the implementation (Step 2), but before finalize, show the DIFF and wait for explicit approval of that specific logic change.
4. Update `docs/lookup/` as the implementation changes.
5. Run full suite: `black .`, `ruff check . --fix`, `pyright`, and `pytest`.

## Phase 4: Final Closure
1. Once all items are done, purge any zombie code or orphaned legacy files.
2. Update the "Done Protocol" in the audit document.
3. Save the key architectural lesson to the Open Brain using `[GOSLING2]`.
