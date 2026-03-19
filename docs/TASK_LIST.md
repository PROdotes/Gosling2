# GOSLING2 MASTER TASK LIST - 2026-03-19

## Phase 1: Compliance & Protocol Recovery [DONE]
- [x] RULE: No Ephemeral MDs (Constitution updated)
- [x] OPEN BRAIN: Persistence rule captured
- [x] AUDIT: Protocol Scars & AI Ghosts
    - [x] Confirm removal of `while` loop N+1 in `CatalogService`
    - [x] Verify every method in `CatalogService` has Entry/Exit logs
    - [x] Check for "Service Leakage" (Raw SQL in Service layer)
- [x] TEST: "Done and Green" Redo
    - [x] Merge standalone publisher tests into `tests/test_catalog.py`
    - [x] Run full project suite (`pytest tests/`)

## Phase 2: Audit Core Integration (Recovered Context) [DONE]
- [x] Spec: `docs/plans/AUDIT_CORE_SPEC.md`
- [x] DOMAIN: Add `AuditAction`, `AuditChange`, `DeletedRecord`
- [x] DATA: `AuditRepository` (Action/Change/Delete getters)
- [x] SERVICE: `AuditService` (History orchestrator)
- [x] API: `/api/v1/audit/history/{table}/{record_id}`
- [x] VERIFY: Timeline merging test (PinkPantheress ID 33 scenario)
- [x] DOCS: Update `docs/lookup/` with new components
- [x] GREEN: 100% test pass on new features and regression suite

## Phase 3: Ingestion Protocol Drafting
- [ ] Spec: `docs/plans/INGESTION_V1_SPEC.md`
- [ ] Implementation:
    - [ ] `POST /api/v1/catalog/ingest`
    - [ ] `DELETE /api/v1/catalog/songs/{id}`
