# THE "DONE AND GREEN" WORKFLOW

This is the exact sequence of actions you must take for every new feature or fix. **MANDATORY**: You must NOT write a single line of `src/` code until the user approves the "1:1:1 Spec-First Agreement".

1. **The 1:1:1 Spec-First Agreement**:
   - PROPOSE the "1:1:1 Agreement" (Signatures, Location, Testing Strategy) in the chat.
   - **Methods**: Which ones and what do they do?
   - **Location**: Where do they go? (No wildcards)
   - **Testing**: How will we prove it's "Green"?
   - **PERMISSION**: Wait for user approval of this agreement.
2. **The Lookup Entry**: 
   - Once approved, update `docs/lookup/*.md` following the **Golden Template** (Rule 3 of Code Index).
   - Log your intent with the "I will now..." phrase as the first line.
3. **The Implementation**: 
   - Implement the feature EXACTLY as defined in the lookup.
   - Implement the tests as outlined in the 1:1:1 agreement.
4. **Verification**: 
   - **THE FULL SUITE RULE**: Run the **FULL** test suite (`pytest`) at the end of every task.
   - It is not enough for *new* tests to pass. You must prove No Regressions.
   - **MANDATORY**: You must physically call `pytest` (without specific file paths) as your final verification step **BEFORE** presenting a code feature for review.
   - **EXEMPTION**: Do NOT run the full test suite for documentation-only changes (lookups, plans, readmes) unless code was also modified in the same turn.
   - Fix until GREEN.
5. **Completion**: 
   - ONLY when the **entire** suite is green, tell the user: "It is done, you can review it."
