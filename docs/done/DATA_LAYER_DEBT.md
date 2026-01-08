# 📉 Data Layer Debt & Refactor Plan

*Status Update (Jan 2026): Major Refactor Success. Core Repositories (Song, Tag, Contributor) Migrated & Audited.*

## 1. Missing Serialization Logic (Prerequisite for Audit Log)

* **`Song.to_dict()`**: **[DONE]**
* **`Tag.to_dict()`**: **[DONE]**
* **`Contributor.to_dict()`**: **[DONE]**
* **`Album.to_dict()`**: **[DONE]**
* **`Publisher.to_dict()`**: **[DONE]**

## 2. Loose SQL Violations (Refactor Targets)

### A. Presentation Layer (`src/presentation/widgets/filter_widget.py`)
* **Violation:** Direct SQL execution (`SELECT DISTINCT ...` for Filters).
* **Fix:** **[DONE]** Refactored `FilterWidget` and `TagPickerDialog` to use Repository methods.

### B. Service Layer (`src/business/services/library_service.py`)
* **Violation:** Direct SQL in `get_distinct_filter_values`.
* **Fix:** **[DONE]** Logic moved to `SongRepository.get_distinct_values()`. Service now purely delegates.

## 3. Repository Migration (The Big Refactor)

*Goal: Adopt `GenericRepository` for Fail-Secure Auditing.*

### A. SongRepository (Priority: Critical)
* **Status:** **[DONE]**
* Inherits `GenericRepository[Song]`.
* Standardized CRUD (`_insert_db`, `_update_db`, `_delete_db`).

### B. TagRepository
* **Status:** **[DONE]**
* Inherits `GenericRepository[Tag]`.
* Manual Audit for `merge_tags`.

### C. ContributorRepository
* **Status:** **[DONE]**
* Inherits `GenericRepository[Contributor]`.
* Implemented `_insert/update/delete`.
* `create` handles connection-aware legacy capability + Audit.
* `merge` manually audits deletions.

### D. PublisherRepository
* **Status:** **[DONE]**
* Inherits `GenericRepository[Publisher]`.
* Implemented `_insert/update/delete`.
* `create` uses `insert`.
