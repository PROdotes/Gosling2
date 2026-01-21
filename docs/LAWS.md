# LAWS: Artist Identity Management

These are immutable laws that protect data integrity in the artist management system.
**DO NOT MODIFY THE APPLICATION TO BYPASS THESE LAWS.**

## LAW 001: ARTIST IDENTITY INTEGRITY

### Rule 1: Unlink Must Split, Not Delete
**When removing an alias/member, SPLIT it into a new Identity. DO NOT delete the name record.**

- **Why:** Deleting a name record destroys credit history
- **Implementation:** `unlink_alias()` creates a new Identity and moves the name there
- **Test:** `test_law_unlink_must_split_not_delete()`

### Rule 2: One Primary Name Per Identity
**Every Identity containing names MUST have exactly one Primary Name.**

- **Why:** Multiple primaries cause the "Gaslighting Bug" (clicking alias opens itself)
- **Implementation:** `_enforce_primary_integrity()` auto-promotes if zero primaries found
- **Test:** `test_law_click_redirection_data_integrity()`

### Rule 3: Rename Collision Requires User Consent
**When renaming an artist to a name that already exists, ALWAYS prompt the user.**

- **Why:** Silent merges destroy user intent (they're fixing a typo, not merging artists)
- **Context:** Renaming is different from purposefully adding an alias
- **User Actions:**
  - **Rename workflow** (fixing typo): `Artist Manager → Edit Name` → Must prompt if collision
  - **Alias workflow** (intentional link): `Artist Manager → Add Alias → Pick Artist` → Can be smart about it
- **Implementation:**
  - Rename: `_save() → _resolve_collision()` ALWAYS shows dialog
  - Add Alias: `_add_alias()` uses smart merge logic (silent if no baggage, prompt if baggage)
- **Test:** `test_law_rename_collision_requires_prompt()` _(needs to be written)_

### Rule 4: Rename+Combine Uses Consume, Not Merge
**When user confirms combining during rename, use `consume()` (delete source), not `merge()` (create alias).**

- **Why:** User is fixing a typo, not creating an alias relationship
- **Behavior:**
  - `consume()`: Transfers credits → Merges identities → **Deletes source name**
  - `merge()`: Transfers credits → Merges identities → **Keeps source as alias**
- **Implementation:** `_resolve_collision()` calls `service.consume()` on user confirmation
- **Test:** `test_law_rename_combine_deletes_source()` _(needs to be written)_

### Rule 5: Add Alias Workflow Uses Merge, Not Consume
**When user purposefully adds an alias, use `merge()` to preserve the alias relationship.**

- **Why:** User explicitly wants to link the names, not delete one
- **Implementation:** `_add_alias()` calls `service.merge()`
- **Test:** `test_law_add_alias_creates_link()` _(needs to be written)_

---

## Summary Table

| User Action | Service Method | Source Name After | Prompts User? |
|-------------|---------------|-------------------|---------------|
| Rename artist (collision) | `consume()` | **Deleted** | ✅ Always |
| Add alias (no baggage) | `merge()` | Kept as alias | ❌ Silent |
| Add alias (with baggage) | `merge()` | Kept as alias | ✅ Prompts |
| Unlink alias | `unlink_alias()` | Becomes new Identity | ❌ Silent |
| Delete artist | `delete()` | Deleted (if no usage) | ✅ Confirms |

---

## Unicode Handling Note

The collision detection uses `py_lower()` for Unicode-aware case-insensitive comparison.
SQLite's `UTF8_NOCASE` collation is NOT used because it doesn't properly distinguish characters like `ć` vs `č`.
