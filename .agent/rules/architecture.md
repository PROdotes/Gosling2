---
trigger: always_on
---

# Architecture & Design Rules

## 1. Architectural Boundaries (The Law)
*   **Strict Layering**:
    1.  **UI** (`src/presentation`): Can talk to Service. **NEVER** Repository. **NEVER** SQL.
    2.  **Service** (`src/business`): Logic & Orchestration. Can talk to Repo. **NEVER** UI Widgets.
    3.  **Data** (`src/data`): SQL & Models. Pure I/O.
*   **Violation is Fatal**: If a task requires breaking this (e.g. SQL in View), **STOP** and Refactor First.

## 2. Code Structure
*   **God Object Ban**: Any file > 600 lines is a critical risk. Logic must be split (e.g., Extract Helper, Split Service). *Note: This mandates proactive prevention for new code and surgical cleaning of legacy methods being modified, not an immediate halt for wholesale refactoring.*
*   **Service Bus**: Sibling widgets (e.g. List vs Filter) MUST NOT talk directly. Use `LibraryService` signals or Event Bus.

## 3. Industrial Amber Design System
*   **No Hardcoded QSS**: Never use `setStyleSheet("color: red")`. Use `theme.qss` and `objectName`.
*   **Component Factory**:
    *   **NEVER** use `QPushButton`, `QLineEdit`, etc directly.
    *   **ALWAYS** use `GlowButton`, `GlowLineEdit`, `Glow...` from `src.presentation.widgets.glow`.

## 4. Resource Management
*   **Config**: Magic numbers belong in `constants.py` or `settings.json`.
*   **Strings**: User-facing text should be centralizable.
