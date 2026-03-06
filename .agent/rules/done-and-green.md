# THE "DONE AND GREEN" WORKFLOW

This is the exact sequence of actions you must take for every new feature or fix. Do not stop in the middle to ask for permission unless you are stuck or need architectural clarification. You must complete the entire cycle before asking for a review.

1. **Write the Specs**: 
   - Check `docs/lookup/` to understand existing structures.
   - Update `docs/lookup/*.md` with the new method signatures, parameters, and return types. This is the Contractual Truth.
2. **Write the Code**: 
   - Implement the feature exactly as defined in the lookup docs.
3. **Test the Code**: 
   - Write the corresponding tests.
   - Run the tests in the terminal.
   - Fix any errors until the tests are GREEN.
4. **Review**: 
   - ONLY when the tests are green and the feature is fully implemented, stop and tell the user: "It is done, you can review it."
