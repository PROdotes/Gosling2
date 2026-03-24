---
description: Strict execution protocol and tool constraint
---

When asked to implement, refactor, or write any code, you MUST follow this state machine strictly:

## Phase 1: Discovery & Planning (READ-ONLY)
1. Read the necessary specifications (`docs/`), lookup files, and codebase context.
2. Present a plan for the **first atomic step only** (e.g., "Step 1: Write test for X").
3. **HARD STOP.** You are strictly FORBIDDEN from using `write_to_file`, `replace_file_content`, `multi_replace_file_content` or `run_command` in this phase.
4. End your response by asking: "Do I have the GO for Step 1?"

## Phase 2: Execution
1. You may ONLY proceed to this phase if the user's latest message gives explicit authorization (e.g., "APPROVED", "GO", "Yes").
2. Execute the single atomic step using your write tools.
3. Run necessary formatters or tests.
4. Present a plan for the next atomic step.
5. **HARD STOP.** Return to the end of Phase 1 and wait for authorization again.