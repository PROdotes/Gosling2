# Gosling2 Test Suite

## 🚨 Consolidation in Progress
We are currently in the process of consolidating the test suite (Task T-04).
Please refer to `docs/specs/T04_TEST_CONSOLIDATION_PLAN.md` for instructions.

## Structure
- `unit/`: Unit tests. Currently fragmented.
- `integration/`: Integration tests.
- `disabled_integrity/`: Tests that are intentionally disabled/broken.
- `fixtures/`: Test data.

## Running Tests
Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

Run all unit tests:
```bash
pytest tests/unit
```
