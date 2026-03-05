# GOSLING3 Testing Constitution (v1.1)

> **"A test that mocks everything tests nothing. A test that ignores Laws is just a suggestion."**

Gosling3 follows a **Law-Based Verification** strategy. We verify the "Invariants" of the system through outcome-focused integration tests. Use of internal mocks for business logic is strictly prohibited.

## 1. The Hierarchy of Proof

### Tier 1: Foundation (Domain Laws / `tests/v3core/laws/`)
**Goal**: Enforce immutable rules of the Gosling data universe (Invariants).
- **Naming Convention**: Test functions MUST be prefixed with `test_LAW_XXX_`, where XXX maps to a documented system law.
- **Verdicts**: Every assertion must include a clear `VIOLATION:` message explaining exactly which rule was broken.
- **Immutables**: e.g., "LAW_001: Every Identity must have exactly one Primary Name."
- **Focus**: These tests protect against critical logic regressions at the model/data layer.

### Tier 2: Orchestration (Integration Paradigms / `tests/v3core/integration/`)
**Goal**: Verify complex data flows and multi-repository logic against a real SQL engine.
- **Fixture**: Use the `mock_db_path` (Hermetic In-Memory SQLite).
- **Scope**: Full "Resolver" loops and lifecycles (e.g. The Grohlton Loop).
- **Data**: Must test using Unicode variants (ć vs č) and fringe edge cases (Orphaned Aliases).

### Tier 3: Reality (Smoke Checks / `tests/v3core/smoke/`)
**Goal**: Verify the Pydantic Layer against the production `gosling2.db`.
- **Constraint**: READ-ONLY. These tests prove our code is synchronized with the actual 100k+ song database schema.

## 2. Professional Standards
1. **The "Ruff" Mandate**: All code must pass `ruff check` before submission.
2. **Violation-Driven Assertions**: DO NOT use plain `assert x == y`. Use `assert x == y, "VIOLATION: Identity {id} lost its primary name during merge!"`
3. **No Internal Mocks**: You are forbidden from mocking Repositories or Services within the v3core suite. If the code talks to a DB, the test runs a DB.
4. **Hermetic State**: Each Tier 1/2 test must start with a clean `executescript(SCHEMA_SQL)` in-memory.

## 3. Automation & Mutation
- **Mutation Testing (`mutmut`)**: Critical logic (like the Identity Resolver) must be resilient to "off-by-one" errors. We will incorporate `mutmut` runs to guarantee our tests fail when logic is altered.
- **Audit Log Law**: Every write operation must be verified by checking the `ChangeLog` table in the same test.
