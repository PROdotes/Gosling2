# Blueprint Skill: The "Needle-Detection" Audit

**Goal**: To prevent "Vibe-Coding" and "Ghost Logic" by proactively identifying every variable, constraint, and side-effect for a Vertical Slice.

## 1. The Schema Scour
Before drafting a Blueprint matrix, you MUST:
- Grep the `schema.sql` for the target tables.
- Check for `ON DELETE CASCADE` vs `SET NULL`.
- Check for `UNIQUE` constraints and `CHECK` validations.
- Verify `IsDeleted` (Soft-Delete) presence.

## 2. The Signature Sync
- Check `docs/lookup/` to ensure the planned signature matches the project's orchestration pattern.
- If the signature is `Optional[ID]`, you MUST define the "None" behavior in the matrix.

## 3. The Constraint Matrix Generation
Generate a Markdown Table for every method in the slice:
- **Inputs**: IDs, raw values, partial/full objects.
- **Hidden States**: Record exists? (Yes/No/Soft-Del). User has permissions? (Yes/No). File present? (Yes/No).
- **Outcome (The Banker Rule)**: Explicitly state the Error Code or Success Result. 
- **NO FALLBACKS**: If you propose a fallback (e.g. "Use default ID if missing"), mark it with ⚠️ for user scrutiny.

## 4. Test Case Derivation
Every row in the Matrix MUST mapped to a future `pytest` or `vitest` case.
