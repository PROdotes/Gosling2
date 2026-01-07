# Testing Strategy & Blueprint (The Constitution)

> **"If it isn't tested, it's broken. If the tests are a mess, the project is a tomb."**

This document is the **Single Source of Truth** for testing in Gosling2. Whether you are a senior architect, an LLM specialist, or a "Bob from 2150," these laws are your binding contract.

---

## 🏛️ The Hierarchy of Laws

When rules conflict, the **Rule of Priority** dictates the path. Laws are listed in order of supreme authority.

### 1. The Law of Separation (The Supreme Law)
**Intent Trumps Structure.** 
Tests must be separated by their **Intent**. Never mix "Feature Logic" with "Robustness Logic" for the sake of convenience or file-count reduction.

| Category | Suffix | Purpose | Speed |
| :--- | :--- | :--- | :--- |
| **Logic (Level 1)** | `test_{comp}.py` | Does the feature work as intended? (Happy Path) | ⚡ Fast |
| **Robustness (Level 2)** | `test_{comp}_mutation.py` | Does it crash with garbage, long strings, or null bytes? | 🐢 Slow |
| **Integrity (Level 3)** | `integrity/test_{x}.py` | Does the code match the database and specs? | ⚡ Fast |

*   **Conflict Resolution**: If Law 2 (Containment) says "Put it in one file" but Law 1 (Separation) says "They have different intents," **Law 1 Wins.** You create two files (e.g., `test_song.py` and `test_song_mutation.py`).

### 🛠️ The Anatomy of Intent (What to test where)

To ensure "Duck-Proofing," you must categorize your tests based on "The Persona of the Input."

#### Level 1: The Logical Developer (Logic)
Tests for the **Happy Path** and **Polite Failures**.
*   **Edge Cases**: Empty fields, properly typed but missing IDs, "Expected" business errors (e.g., trying to play a non-existent file).
*   **Goal**: Ensure the feature works as documented in the Specs.

#### Level 2: The Chaos Monkey (Robustness)
Tests for the **Malicious Actor** and **Hardware Nightmares**.
*   **Security**: SQL Injection (Bobby Tables) in search fields; Null-byte injection in file paths.
*   **Corruption**: Partially written files, corrupt ID3 headers, "Zero-byte" MP3s.
*   **Exhaustion**: 100,000-character titles, deeply nested JSON, memory-leak triggers.
*   **Environment**: Disk Full errors, Permission Denied (OS level), Network timeouts.
*   **Goal**: Ensure the application **DOES NOT CRASH**. It can fail, but it must fail without a Segfault or data corruption.

### 2. The Law of Mirroring
The `tests/` directory **MUST** mirror the `src/` directory exactly.
*   **Source**: `src/data/repositories/song_repository.py`
*   **Test**: `tests/unit/data/repositories/test_song_repository.py`

### 3. The Law of Containment
**One Component = One Logic File.**
*   All functional logic for `MetadataService` goes into `test_metadata_service.py`.
*   Do NOT create new files for individual bugs (e.g., `test_bug_fix_1.py` is **forbidden**). Use **Nested Classes** within the main file to organize edge cases.

### 4. The Law of Unity (Fixtures)
*   **Global**: Use `tests/conftest.py` for shared mocks (DB, Mutagen fixtures, Headless Qt).
*   **Local**: Use `setUp(self)` for class-specific mocks. Never copy-paste `setUp` logic.

### 5. The Law of Coverage (When to Test)
**Test what could break.** Not everything requires a test, but every *decision* does.

|| Layer | Filename | Purpose | Speed |
||-------|----------|---------|-------|
|| **1. Logic** | `test_{component}.py` | Does the feature work? (Happy Path & Basic Errors) | ⚡ Fast |
|| **2. Robustness** | `test_{component}_mutation.py` | Does it crash with garbage inputs? (Fuzzing, Injection) | 🐢 Slow |
|| **3. Integrity** | `tests/unit/integrity/` | Does the Code match the Database & Specs? | ⚡ Fast |

Mutation testing (including any use of `scripts/mutation_test.py`) must stay in **Robustness** tests and never be mixed into normal Logic tests. Keep mutation assertions and scenarios in their own dedicated files so they can be run and tuned independently.


| Must Test | May Skip |
|---|---|
| Methods with logic (`if`, `try`, loops, calculations) | Trivial accessors (one-line getters/setters) |
| New public methods with behavior | Pass-through orchestration (if upstream/downstream are tested) |
| — | Simple data mappers (row-to-object, object-to-dict) if transitively tested through caller tests |

**The Boundary Rule:** Test at the point of responsibility. If `Repository.get()` sanitizes data, `Service.move()` does not re-test sanitization. If `get()` breaks, the failure shows in `test_repository.py`, not `test_service.py`.

---

### 6. The Law of Derivation (Where Tests Come From)
Tests are derived from **two sources**:

| Source | Produces | Examples |
|---|---|---|
| **Feature Spec** | Logic Tests | "Year must be 1900–current" → test 1899, 1900, current, current+1 |
| **This Testing Bible** | Robustness Tests | Standard garbage: `""`, `null`, `-1990`, `"abc"`, injection strings |

**The Line:** If the Spec documents a constraint, testing at its boundary is **Logic**. Testing garbage the Spec doesn't mention is **Robustness**.

---

### 7. The Law of Trust Boundaries (When to Create `_mutation.py`)
Not every component needs robustness tests. Only those at **trust boundaries**:

| Input Source | Trust Level | Needs `_mutation.py`? |
|---|---|---|
| External files (ID3 tags, downloads) | 🔴 Untrusted | **Yes** |
| User input (search, forms) | 🔴 Untrusted | **Yes** |
| Own database (sanitized on write) | 🟢 Trusted | **No** (unless testing corruption) |
| Internal function calls | 🟢 Trusted | **No** |

**Robustness Categories** (apply only what's relevant):
- Corrupt/malformed input (file parsers)
- Injection (SQL, null-byte, path traversal)
- Exhaustion (huge strings, deep nesting)
- Environment failure (disk full, permission denied)
- Wrong types (`null`, empty, negative, wrong data type)

---

## 📂 Physical Cleanup (The "No Litter" Rule)
A task is not **Done** when the code passes; it is Done when the directory is clean.
1.  **Consolidate**: Move logic to the Target File.
2.  **Verify**: Run `pytest`.
3.  **Flush**: Delete the source/orphaned files immediately. Orphaned files are "liabilities" that confuse future developers (and AI).

---

### 8. The Law of Inventory (The Enforcer)
**"Trust, but Verify."**
*   **The Rule**: Every file in `src/` (excluding `__init__.py` and simple constants) **MUST** have a corresponding validation file in `tests/`.
*   **The Check**: Use `python tools/audit_test_coverage.py` to enforce this.
*   **The Standard**:
    *   **Logic Tests**: Required for ALL files.
    *   **Mutation Tests**: Required for Trust Boundaries (Law 7).
    *   **Coverage**: Minimum 80% per file.
*   **The Exemption** (Aligning with Law 5):
    *   Files that meet Law 5's "May Skip" criteria (e.g., pure constants, abstract interfaces) must be explicitly added to `tools/test_audit.ignore`.
    *   **Rule**: Silent skipping is forbidden. You either Test it or Ignore it explicitly.

### 9. The Law of Silence (No Interactivity)
**Tests Wait for No One.**
UI tests must be completely non-interactive. Any component that normally triggers a message box (`QMessageBox`) must be silenced in tests.
*   **Protocol**: Use a `silence_popups` fixture (global or local) to patch `information`, `warning`, `critical`, and `question`.
*   **Standard Mock**: `QMessageBox.question` should generally return `QMessageBox.StandardButton.Yes` to follow the "Happy Path" by default, unless test-specific behavior is needed.

---

## 🛡️ The "Yelling" Safety Net (Integrity)
Gosling2 uses **Yellberus** (in `tests/unit/integrity/`).
*   It ensures the Database Schema and Song Model are in sync.
*   **Rule**: Never disable an Integrity test to "pass" a build. If it yells, the code is incomplete.

---

## 📋 Audit Coverage Canary Test
Location: `tests/unit/test_audit_coverage.py`

This test **automatically detects missing audit logging** by scanning the codebase for CRUD operations.

### What it checks:
1. **`test_all_crud_operations_have_audit_logging`** - Scans for `INSERT/UPDATE/DELETE` SQL and verifies the method has `AuditLogger` + `batch_id` patterns
2. **`test_no_audit_logger_without_batch_id`** - Catches any `AuditLogger(conn)` calls missing `batch_id=`

### Exclusions (by design):
- `presentation/` - UI goes through services, not direct DB
- `database.py` - Schema init doesn't need auditing  
- `_insert_db`, `_update_db`, `_delete_db` - Called by audited `GenericRepository` methods
- Audit tables (`ChangeLog`, `DeletedRecords`, `ActionLog`) - Can't audit themselves
- `Roles` - Static lookup table

### Why it exists:
LLMs tend to add CRUD operations without corresponding audit logging. This canary test **fails CI** if anyone forgets to audit a database write.

---

## 🤖 Specialist/LLM Protocol (The Duck Test)
Before you (The Agent) commit any test changes, you must answer these three questions:
1.  **Is this a Logic test or a Mutation test?** (If it's both, split the file).
2.  **Does the file path mirror `src`?**
3.  **Are there orphaned 'Litter' files still in the directory?**

---

## 🚀 Quick Run Commands

### For Humans (Direct pytest)
```bash
# Run Logic only
pytest tests/unit/ -k "not mutation"

# Run everything
pytest

# Run with coverage
pytest --cov=src
```

### For Agents/CI (Use wrapper script)
The `tools/run_tests.py` wrapper solves PowerShell encoding issues and saves clean output to `test_output.txt`:
```bash
# Run all tests (output saved to test_output.txt)
python tools/run_tests.py

# Run with specific options
python tools/run_tests.py -x --tb=long    # Stop on first failure
python tools/run_tests.py tests/unit/     # Run only unit tests
python tools/run_tests.py -q --tb=no      # Minimal output
```

**Why the wrapper?** PowerShell mangles pytest's progress bars and ANSI codes. The wrapper captures output with proper UTF-8 encoding.
