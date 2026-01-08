# T-101: Surgical Credits (The "Grohl" System)

**Status**: Backlog (Sanity Checked)
**Priority**: Low
**Complexity**: Medium

## 🎯 Goal
Enable fine-grained "Jobs" for contributors (e.g., "Guitarist", "Drummer", "Engineer") beyond the primary four roles (Performer, Composer, Lyricist, Producer).

## 📊 Current Architecture Support
The underlying database schema is already relational and supports this via the `SongCredits` table:
*   `SongCredits(SourceID, CreditedNameID, RoleID)`
*   This means a single person can have multiple roles on the same song.

## 🚧 Known Gaps (The "Wait" List)

### 1. Dynamic Roles (Service Layer)
Currently, the `Roles` table is seeded with fixed entries.
*   **Need**: `ContributorService.get_or_create_role(role_name)` so users can add "Vibraphonist" on the fly.

### 2. ID3 Frame Complexity (Packing Logic)
Standard tags like Title or Genre are 1:1 mappings. "Jobs" are many-to-many and use complex ID3 frames:
*   **TMCL** (Musician Credits List): Required for internal jobs like "Guitarist".
*   **TIPL** (Involved People List): Required for production jobs like "Mastering Engineer".
*   **Format**: These frames use null-separated strings: `Role\0Name\0Role\0Name`. 
*   **Gap**: `MetadataService` needs a "Packer" to gather all database credits for a song and serialize them into these specific string formats.

### 3. UI Implementation
We need a "Multi-Pick" workflow similar to the **Tag Picker**:
1.  **Select Identity** (e.g., Dave Grohl)
2.  **Select Role** (e.g., Guitarist)
3.  **Result**: A chip displayed as `Guitarist: Dave Grohl`.

## 🛠️ Implementation Steps (When Prioritized)
1.  **Refactor**: Update `ContributorService` to support dynamic role creation.
2.  **Registry**: Add `InvolvedPeople` and `Musicians` virtual fields to `yellberus.py`.
3.  **Core**: Implement `TIPL` / `TMCL` serialization logic in `MetadataService`.
4.  **UI**: Create `CreditPickerDialog` (fork/variation of `TagPickerDialog`).
