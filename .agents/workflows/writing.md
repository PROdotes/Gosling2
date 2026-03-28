---
description: Strict execution protocol and tool constraint
---

When asked to implement, refactor, or write any code, you MUST follow this state machine strictly:

## Phase 1: Discovery & Planning (READ-ONLY)
1. Read the necessary specifications (`docs/`), lookup files, and codebase context.
2. Present a plan for the **task** (see "What is a Task?" below).
3. **HARD STOP.** You are strictly FORBIDDEN from using `write_to_file`, `replace_file_content`, `multi_replace_file_content` or `run_command` in this phase.
4. End your response by asking: "Do I have the GO?"

## Phase 2: Execution
1. You may ONLY proceed to this phase if the user's latest message gives explicit authorization (e.g., "APPROVED", "GO", "Yes", "sure", "ok").
2. Execute the **entire agreed-upon task** using your write tools. This includes all files, helpers, schema tweaks, and test updates that naturally follow from the agreement.
3. Run necessary formatters or tests.
4. Present a summary of what changed and ask what's next.

## What is a Task?

A task is NOT defined by method count, file count, or lines of code. It is defined by the **logical change that was agreed upon** in conversation.

**Examples:**
- "Align ProcessingStatus to the spec" = one task, even if it touches 4 files (repo, mapper, service hook, tests).
- "Add a helper method that the agreed-upon feature obviously needs" = part of the same task.
- "Fix a 1-line schema comment while I'm in there" = part of the same task.

**The test:** Can the user review the resulting diff and hold the entire flow in their head? If yes, it's one task.

**Violations:**
- Implementing a completely new feature or subsystem that was never discussed.
- Stopping to ask permission for every trivial line change that obviously falls within the agreed scope.
- Going off and hardcoding specs without asking questions first when the requirements are ambiguous.

## Authorization Gate

Before writing ANY code, classify the user's message:

| Signal | Example | Action |
|--------|---------|--------|
| **Imperative** | "fix this", "implement X", "align Y" | Plan the task, present it, wait for GO. |
| **Informational** | "I added a new doc", "check this out" | READ ONLY. Summarize findings, ask what to do. |
| **Analytical** | "what do we still need", "how does Y work" | REPORT ONLY. No code. |

If in doubt, **ask**.