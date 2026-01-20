---
name: Core Protocol
description: The fundamental operating directives for the Gosling Agent. Defines interaction style, scope management, and architectural philosophy.
---

# The Gosling Core Protocol
**NOTE: Primary Directives (Process, Scope, Philosophy) are now enforced via `rules/operating_directives.md`.**

This skill defines extended context on how to interpret those directives.

## 1. Extended Philosophy
*   **The "Tomorrow Rule"**: We maintain this code tomorrow. If a fix is fast but messy, it violates the rule.
*   **Blueprint First**: Writing the 'why' and 'how' prevents logic errors before they start.


## 4. Architectural Boundaries
*   **Service Layer**: Business logic goes here (`src/business`).
*   **Presentation Layer**: UI widgets go here (`src/presentation`).
*   **Data Layer**: Repositories and Models go here (`src/data`).
*   **Strict Separation**: Widgets should never talk directly to Repositories. They must go through a Service.

## 5. Refactor-First Mandate
*   **Stop & Report**: If a requested user task involves editing a file that currently violates architectural boundaries (e.g., zip logic in `MainWindow`, SQL in `View`), you must **STOP**.
*   **Propose Cleanup**: Do not build new features on top of broken foundations. Ask the user for permission to move the offending logic to its correct layer (Service/Repository) **FIRST**.
*   **Fix Then Feature**: Only proceed with the user's original request once the structural integrity is restored.
