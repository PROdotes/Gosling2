# v0.2 Technical Debt & Major Refactoring Plan

**Status**: DEFERRED (Focus is on v0.1 Feature Completion & Backlog Processing)
**Goal**: Capture architectural improvements without distracting from current GSD mode.

## 1. The Leviathans Split (T-28)
**Target**: `src/presentation/widgets/library_widget.py` (> 3000 lines)
**Issue**: God Object handling View, Controller, Business Logic, and Drag/Drop.
**Plan**:
*   Extract `DragDropHandler` class.
*   Extract `FilterLogic` (currently mixed with UI checks).
*   Extract `ContextMenuManager`.
*   Moved `DropIndicatorHeaderView` to separate file.

## 2. The Clean Core (Parallel Construction)
**Target**: Entire Architecture
**Issue**: Dependency tangles (hydra problem).
**Plan**:
*   Build a "Clean Core" (Models + Pure SQL Repos + Pure Services) that has **ZERO** dependencies on existing UI code.
*   Implement new features using this core.
*   Migrate old features one by one (Strangler Fig pattern).
*   **Strategy**: See `docs/proposals/PROPOSAL_REMOTE_TERMINAL.md` (MVP: Flask API + Simple Web UI) to enforce separation.

## 3. Async Background Operations
**Target**: `LibraryService`, `TagService`
**Issue**: UI freezes during large batch operations (Save, Rename, mass Tagging).
**Plan**:
*   Move `save_changes` and `rename_files` to `Worker` threads.
*   Implement `TaskQueue` for sequential file operations to avoid race conditions.

## 4. Single Source of Truth (SSOT)
**Target**: Completeness Checks & Filtering
**Issue**: Completeness logic exists in UI loops (`_check_value_match`) and Helper functions (`yellberus`).
**Plan**:
*   Move `is_complete` calculation to Database (Generated Column) or Service.
*   UI should only read the bool, not calculate it.

## 5. Strict Typing & Blast Radius
**Target**: Data Contracts
**Plan**:
*   Enforce `Blast Radius Analysis` for all schema changes (grep usage, audit consumers).
*   Use strictly typed Data Transfer Objects (DTOs) instead of loose dicts/tuples between layers.
