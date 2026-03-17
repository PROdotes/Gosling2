# GOSLING2 CONSTITUTION

This document consolidates all project-level protocols and rules to ensure architectural integrity and prevent "vibe-coding" slop.

---

## 1. Spec-First Protocol
1. **MANDATORY WISDOM CHECK**: Before planning, search Open Brain for macro concepts (e.g., 'WebSockets', 'Lambda binding').
2. **1:1:1 AGREEMENT**: We must agree on what methods, where they go, and how we test them before code is written.
3. **SPEC APPROVAL**: Write code only after plan approval. If rejected, fix the spec/plan first.
4. **PLANNING**: Non-trivial changes require a short plan/spec in `docs/` before implementation.

---

## 2. The Lookup Protocol (Code Index)
1. **MANDATORY LOOKUP**: Check `docs/lookup/` before research or changes. It is the "Map of the Territory."
2. **SQL FIRST**: **NEVER** modify `domain.py` models or parsing logic without first inspecting `schema.py` or the raw `sqlite3` tables. Pydantic models must reflect physical database realities, not assumptions.
3. **GOLDEN TEMPLATE**: Every lookup entry must follow this format:
   - Header (# Name)
   - Location (*Location: path*)
   - Responsibility (**Responsibility**)
   - Signatures (### signature)
4. **STRICT SIGNATURES**: Every method must have a strict Python signature. Vague descriptions are violations.
5. **LOCATION DEFINITION**: Every entry must have a single, definitive file path.
6. **NO VIBE-CODING**: Do not crawl raw source code if a lookup entry exists.

---

## 3. The Debug Protocol (Log It First)
1. **NO BLIND GUESSING**: Do not theorize architectural failures without evidence.
2. **PROVE IT FIRST**: Repro and analyze exact output before writing patches.
3. **ENTRY/EXIT INSTRUMENTATION**: Services and Repositories must log "Entry" (args) and "Exit" (found/failed).

---

## 4. Open Brain & Persistent Memory
- **OPEN BRAIN**: Stores permanent lessons, "scars," and workflow preferences via MCP.
- **LOCAL DOCS**: Project state (schemas, stack, structure) belongs in `docs/`, not the Brain.
- **PREFIXES**: Use `[GOSLING2]` or `[GLOBAL]` for all brain operations.
- **SEARCH BEFORE ACTING**: Search brain when starting sessions, drafting specs, or hitting familiar bugs.

---

## 5. Metadata & Context Health
- **STEP COUNTING**: Include the current Step Id at the beginning of every response.
- **FRESH START**: Suggest a fresh chat if step count exceeds 500 or performance drifts.

---

## 6. The "Done and Green" Protocol (Coding End Rules)
A task is **NOT** "Done" until the following Automated Engineering Loop is 100% complete:
1.  **LOOKUP SYNC**: `docs/lookup/` is perfect and 100% accurate to the implementation.
2.  **INSTRUMENTATION**: `src.services.logger` instrumentation is pervasive (Traceable entry/exit/violation).
3.  **CLEANUP**: All "zombie code," dead feature references, and orphan files are purged. No "AI ghosts" or summaries in source code.
4.  **LINTING**: Use automated tools (`black .` for formatting and `ruff check . --fix` for AST/import cleanup) to ensure code passes linting with 0 errors. No manual formatting.
6.  **THE FULL SUITE RULE**: `pytest` passes on the **entire project test suite**, not just the new tests. Regression testing is non-negotiable.
7.  **100% COVERAGE**: New code MUST have 100% test coverage. No "Done" state exists until `pytest --cov` proves every new line is executed.
