---
trigger: always_on
---

# Architecture & Design Rules

## 1. Architectural Boundaries (The Law)
*   **Strict Layering**:
    1.  **UI** (`src/presentation`): Can talk to Service. **NEVER** Repository. **NEVER** SQL.
    2.  **Service** (`src/business`): Logic & Orchestration. Can talk to Repo. **NEVER** UI Widgets.
    3.  **Data** (`src/data`): SQL & Models. Pure I/O.
*   **Violation is Noted**: If a task requires editing a file that breaks layering, **DO NOT STOP**. Mention the violation in **Field Notes** at the end. The **GSD Protocol** (Turbo Mode) always overrides architectural purity for functional milestones.

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

## 5. Facade Integrity (The Orchestrator Rule)
*   **Completeness**: Facade services (e.g., `ContributorService`) MUST expose all necessary operations from their underlying domain services (`IdentityService`, `ArtistNameService`) if the UI requires them.
*   **Delegation**: Always prefer delegating to an existing domain service method over re-implementing logic in the facade.
*   **Consistency**: Ensure method signatures in the facade align with the domain service to maintain predictable behavior.
