# Spec: docs/lookup/junk_detector.md

## Overview
As per GOSLING2 Rule 9 (Deduplication First), we need a centralized manifest of "Junk" — duplicated logic, redundant documentation, and architectural bloat. This manifest serves as a hit-list for refactoring and a guide to prevent further duplication.

## Target: docs/lookup/junk_detector.md

### Section 1: Documentation Redundancy
Lists methods documented in multiple lookup files. 
*Rule*: If a Service method is just a pass-through to a Repo method, the detail belongs in the Repo lookup; the Service lookup should only list the signature and a pointer (e.g., `(-> Repo)`).

### Section 2: Logic Duplication (Structural)
Lists methods or SQL fragments that are identical across repositories.
*Example*: `add_credit` logic in `SongCreditRepository` vs `AlbumCreditRepository`.

### Section 3: Name Ambiguity / Collisions
Lists methods with identical names but different behaviors or return types.
*Example*: `get_by_path` in `MediaSourceRepository` (returns `MediaSource`) vs `SongRepository` (returns `Song`).

### Section 4: Vertical Slice Seams (Zombies)
Lists Router endpoints that are documented but unused by any JS caller in `src/static/js/dashboard/api.js`.

---

## Initial Audit Findings

### 1. Documentation Redundancy
- `get_all_roles`: in `data.md` and `services.md`.
- `update_publisher`: in `data.md` and `services.md`.
- `get_all_identities`: in `data.md` and `services.md`.
- `search_identities`: in `data.md` and `services.md`.
- `add_song_publisher`: in `data.md` and `services.md`.

### 2. Structural Duplication (Candidate for Refactoring)
- `add_credit`: Duplicated in `SongCreditRepository` and `AlbumCreditRepository`. 
- `insert_credits`: Duplicated in `SongCreditRepository` and `AlbumCreditRepository`. (Wait, let's check).
- `get_or_create_credit_name`: In `SongCreditRepository`. Is it needed in `AlbumCreditRepository` too?

### 3. Name Ambiguity
- `get_by_path`: Base Record vs Song Specialized Record.
- `get_by_hash`: Base Record vs Song Specialized Record.
- `search_slim`: Song Search vs Album Search.

---

## Verification Protocol
1. Any new method must be checked against `docs/lookup/junk_detector.md`.
2. If a method in `services.md` is marked "(-> Repo)", do not duplicate its full documentation there.
