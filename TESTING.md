# Testing Strategy & Blueprint

> **"If it isn't tested, it's broken."**

This document is the **Single Source of Truth** for testing in Gosling2. Whether you are a senior architect or "Bob from Accounting" learning to code, follow these rules to ensure the codebase remains robust and maintainable.

---

## 📜 The Constitution of Testing

We adhere to four immutable laws to prevent "Test Sprawl":

### 1. The Law of Mirroring
The `tests/` directory **MUST** mirror the `src/` directory exactly.
*   **Source**: `src/data/repositories/song_repository.py`
*   **Test**: `tests/unit/data/repositories/test_song_repository.py`

### 2. The Law of Containment
**One Component = One Test File.**
*   Do NOT create new files for bugs or edge cases (e.g., `test_playback_bug_123.py` is **forbidden**).
*   All functional logic for `PlaybackService` goes into `test_playback_service.py`.
*   **Solution**: Use **Nested Classes** to organize large files.
    ```python
    class TestPlaybackControls(unittest.TestCase): ...
    class TestPlaybackPlaylist(unittest.TestCase): ...
    class TestPlaybackErrors(unittest.TestCase): ...
    ```

### 3. The Law of Separation
Tests are categorized by their **Intent**. Do not mix them.

| Layer | Filename | Purpose | Speed |
|-------|----------|---------|-------|
| **1. Logic** | `test_{component}.py` | Does the feature work? (Happy Path & Basic Errors) | ⚡ Fast |
| **2. Robustness** | `test_{component}_mutation.py` | Does it crash with garbage inputs? (Fuzzing, Injection) | 🐢 Slow |
| **3. Integrity** | `tests/unit/integrity/` | Does the Code match the Database & Specs? | ⚡ Fast |

### 4. The Law of Unity
**Unify your Fixtures.**
*   Do not copy-paste `setUp` logic across 50 files.
*   Use `conftest.py` for global needs (e.g., Mock Database, Headless Qt App).
*   Use `setUp(self)` for class-specific needs.

---

## 🚀 Quick Start: How to Add a New Test

So you wrote a new function `calculate_bpm()` in `src/audio/analyzer.py`. Here is how you test it:

### Step 1: Find the Home
*   Go to `tests/unit/audio/`.
*   Is there a `test_analyzer.py`?
    *   **Yes**: Open it.
    *   **No**: Create it.

### Step 2: Choose Your Section
*   Inside `test_analyzer.py`, find the relevant Class.
*   If testing a new feature, add a new class:
    ```python
    class TestBpmCalculation(unittest.TestCase):
        def test_calculate_bpm_techno(self):
            # ...
    ```

### Step 3: Run It
```bash
# Run ONLY your file (Fast)
pytest tests/unit/audio/test_analyzer.py

# Run everything (Sanity Check)
pytest
```

---

## 🛡️ The "Yelling" Safety Net (Integrity Tests)

Gosling2 uses a specialized system called **Yellberus** (located in `tests/unit/integrity/`).

**What it does**:
It ensures the Database, the Code, and the UI are 100% synchronized.
*   If you add a column `Genre` to the Database...
*   But forget to add it to the `Song` model...
*   **The System Yells**: `IntegrityError: Column 'Genre' found in DB but missing in Song model.`

**Rule**: Never disable an Integrity test. If it yells, **you** are wrong (or the code is incomplete). Fix the code to match the schema.

---

## 🧪 Best Practices (The "Do's and Don'ts")

### ✅ DO
*   **Use Fixtures**: If you need a database, request `temp_db` (if available via conftest).
*   **Test the "Why"**: `test_play_pauses_when_empty` is better than `test_play_2`.
*   **Mock External interactions**: Don't actually call the filesystem if you can mock it (unless testing the Repository).

### ❌ DON'T
*   **Don't Sleep**: Never use `time.sleep(1)`. Use `qtbot.wait()` or polling.
*   **Don't touch `src` from `tests`**: Import properly, don't modify source files during tests.
*   **Don't catch `Exception`**: Be specific. `except ValueError:` is better than `except Exception:`.

---

## 📂 Test Suite Structure

```text
tests/
├── integration/        # Real interactions (Repo + Service + DB)
├── unit/
│   ├── business/       # Service Logic
│   ├── data/           # Repositories & Models
│   ├── integrity/      # Schema & Contract Managers (Yellberus)
│   ├── presentation/   # UI Widgets
│   └── conftest.py     # Global Fixtures
└── requirements-test.txt
```
