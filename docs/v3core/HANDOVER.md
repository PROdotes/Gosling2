# Phase 0 → Phase 1: V3CORE HANDOVER

> [!IMPORTANT]
> **READ THIS BEFORE COMMENCING PHASE 1.** Do not "vibe-code" or guess what is current. 
> There is legacy code in `src/` and `src/v3core/` that has been explicitly killed or refactored.

## 1. The Global Status
- **Phase 0 (Foundation)**: ✅ **COMPLETE**. (Domain models, Batch Identity Resolver, SQLite Schema, Testing Constitution).
- **Current Frontier**: Phase 1 (The Engine / FastAPI Background Service).

## 2. Inmutable Laws (The Scars)
1. **No N+1 Queries**: Never loop through IDs in Python and call the DB individually. Use `resolve_name_pool([ids])` in `IdentityRepository`.
2. **Grohlton Check Rule**: 
   - **Person**: Own aliases + Groups they are in.
   - **Group**: Own aliases only. No member-leaking.
3. **Pydantic lockdown**: All `v3core` models use `extra="forbid"`. If you see model drift, fix the DB schema first.
4. **Law-Based Testing**: All tests must follow the `test_LAW_XXX_` convention and include `VIOLATION:` messages in assertions. No internal mocks allowed.

## 3. Directory of Truth
- **Models**: `src/v3core/models/domain.py`
- **Resolver**: `src/v3core/services/identity_service.py` (Stateless & Batch-Aware). 
- **Tests**: `tests/v3core/laws/` (The Laws of Physics).
- **Contracts**: `docs/lookup/` (Updated *before* implementation).

## 4. Killed Zombie Code (Do Not Restore)
- **`IdentityRepository.get_memberships`**: DELETED. Replaced by SQL-heavy `resolve_name_pool`.
- **`IdentityService._expand_identity`**: DELETED. Recursive logic was a performance-killing "virus."

## 5. Next Steps
1. Initialize `src/v3engine/` (FastAPI).
2. Wire up the `IdentityService` to a REST endpoint.
3. Establish the Audio Playback thread separate from the UI.
