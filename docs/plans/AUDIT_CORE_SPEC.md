# Spec: Audit Core Integration

## Overview
This plan outlines the integration of the "Dark" audit tables (`ActionLog`, `ChangeLog`, `DeletedRecords`) into the GOSLING2 application. This will allow the system to expose the historical context of every record, which is critical for understanding "ID Drift" and "Identity Fractures."

## Proposed Changes

### Domain Models ([src/models/domain.py](file:///c:/Users/glazb/PycharmProjects/gosling2/src/models/domain.py))
- [NEW] Add `AuditAction`: Represents a high-level event (IMPORT, DELETE, etc.).
- [NEW] Add `AuditChange`: Represents a field-level modification (Old vs. New).
- [NEW] Add `DeletedRecord`: Represents a JSON snapshot of a purged record.

### Data Layer (`src/data/audit_repository.py`)
- [NEW] **`AuditRepository`**:
    - `get_actions_for_target(target_id: int, table: str)`: Fetch from `ActionLog`.
    - `get_changes_for_record(record_id: int, table: str)`: Fetch from `ChangeLog`.
    - `get_deleted_snapshot(record_id: int, table: str)`: Fetch from `DeletedRecords`.

### Service Layer ([src/services/catalog_service.py](file:///c:/Users/glazb/PycharmProjects/gosling2/src/services/catalog_service.py))
- [MODIFY] **[CatalogService](file:///c:/Users/glazb/PycharmProjects/gosling2/src/services/catalog_service.py)**:
    - Add `get_history(record_id, table)`: A high-level orchestrator that merges actions and changes into a unified timeline.

### API Layer (`src/api/routers/audit.py`)
- [NEW] **`audit` Router**:
    - `GET /api/v1/audit/history/{table}/{id}`: Returns the full timeline for a record.

---

## Verification Plan

### Automated Tests
- **`pytest tests/integration/test_audit.py`**:
    - Verify that known `ChangeLog` entries for NameID 33 (PinkPantheress -> Ines Prajo) are correctly retrieved and formatted.
    - Verify that `DeletedRecords` snapshots can be parsed back into Domain Models.

### Manual Verification
- Use `curl` or a browser to hit `/api/v1/audit/history/ArtistNames/33` and verify the output shows the transition from "PinkPantheress" to "Ines Prajo" with the correct timestamps.
