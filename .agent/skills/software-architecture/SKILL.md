---
name: Software Architecture
description: The blueprints and structural laws of Gosling2. Enforces strict layering and modularization.
---

# Gosling2 Architecture Standards

This skill governs the *structural* decisions of the codebase. It is the "Building Code" that prevents spaghetti logic.

## 1. The Layered Hierarchy
Data flows strictly **Down**, events flow **Up**.

### Level 1: Presentation (UI)
*   **Location**: `src/presentation/`
*   **Responsibility**: Displaying data, capturing input, animations.
*   **Forbidden**: Direct SQL, File I/O, Business Logic.
*   **Dependencies**: Can import `src/business` (Services). **Cannot** import `src/data` (Repositories).

### Level 2: Business (Services)
*   **Location**: `src/business/`
*   **Responsibility**: Orchestration, Validation, Complex Calculation, Transaction Management.
*   **Forbidden**: `PyQt` widgets (signals/slots are okay), SQL.
*   **Dependencies**: Can import `src/data` (Repositories).

### Level 3: Data (Repositories)
*   **Location**: `src/data/`
*   **Responsibility**: CRUD operations, SQL queries, DTO mapping.
*   **Forbidden**: Business Logic (e.g., "Calculate royalty"), UI code.
*   **Dependencies**: Can import `src/core`.

### Level 4: Core (Shared)
*   **Location**: `src/core/`
*   **Responsibility**: Constants, Logging, Utilities, Exceptions.
*   **Dependencies**: None (Leaf nodes).

## 2. The Law of Modularization
*   **God Object Ban**: Any file exceeding **600 lines** is considered a "God Object Risk".
*   **Action**: If you need to add code to a file > 600 lines, you must first propose a **Split**.
*   **Splitting Strategy**:
    *   **UI**: Split by visual component (e.g., `SearchBar`, `FilterTree`).
    *   **Service**: Split by domain (e.g., `SongService` vs `PlaylistService`).
    *   **Utilities**: Split by function (e.g., `string_utils.py`, `file_utils.py`).

## 3. The Service Bus Pattern
*   **Communication**: Sibling widgets (e.g., FilterTree vs Table) must **NOT** talk directly.
*   **Mechanism**: They communicate via `LibraryService` signals or a dedicated `EventBus`.

## 4. Resource Management
*   **UI Styling**: Strict ban on inline headers. Use `theme.qss`.
*   **Strings**: User-facing text should be centralizable (prepare for i18n).
*   **Config**: Hardcoded magic numbers belong in `constants.py` or `settings.json`.
