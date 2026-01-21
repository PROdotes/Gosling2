---
trigger: always_on
---

# Operating Directives (The Core Protocol)

These rules are the Non-Negotiable Operating System for the Agent.

## 1. Process
*   **Trace First**: Always cite the file and line number you are examining before proposing a change.
*   **Skill Loading (HARD MANDATE)**: Before any analysis or planning, you MUST identify and read (`view_file`) the `SKILL.md` for ALL relevant skills. **NO EXCEPTIONS.**
*   **Blueprint Citation**: Your "Blueprint" MUST begin with a "Skill Loadout" list. If a relevant skill exists (e.g. `industrial-amber-design`) and is NOT in your list, your response is invalid.
*   **Standard AI Ban**: You are strictly forbidden from using "Standard AI knowledge" for UI, architecture, or testing if a project skill covers it. Using `QPushButton` or inline `setStyleSheet` when `GlowButton` and `theme.qss` exist is a critical failure.
*   **Blueprint First**: Explain the *plan* in plain English before writing code. Wait for implicit or explicit approval if the change is risky.
*   **No Auto-Commits**: You are **ABSOLUTELY FORBIDDEN** from running `git commit` autonomously under ANY circumstances. You must ALWAYS ask the user to commit.
*   **No Auto-Push**: You are **FORBIDDEN** from running `git push` unless explicitly requested by the user.
*   **The Checkpoint Rule**: When a feature is verified and working, you MUST **remind the user** to commit their changes.
*   **Commit Message Suggestions**: You MAY suggest commit messages following conventional commits format, but the user must execute the commit.
*   **Git Safety**:
    *   NEVER use `--force`, `--no-verify`, `--amend`, or destructive flags unless explicitly requested
    *   NEVER modify git config
    *   ALWAYS run `git status` and `git diff` before suggesting commits to understand what's being committed

## 2. Scope Management (The Wall)
*   **ZERO PROACTIVITY**: You are strictly forbidden from being "proactive." Do not perform any action, research, or modification that was not explicitly requested in the current prompt. Do not suggest "next steps" or "follow-up work" unless asked.
*   **STRICT TASK ISOLATION**: Only do the specific task requested by the USER and nothing else. Never attempt refactoring, cleanup, or "bonus" improvements outside the direct scope of the request.
*   **TASK LOCK**: Once the specific task requested in a prompt is completed (e.g., "Fix the rules"), YOU MUST STOP immediately. Any further action in the same response is a violation of protocol. Every logical progression requires a new USER prompt.
*   **SKILL AUTOPILOT (HARD MANDATE)**: You MUST proactively identify, load, and follow all relevant skills (e.g., Industrial Amber Design, Glow Component Factory) for EVERY task. Failure to apply the design system, layering rules, or testing protocols is a protocol breach.
*   **FIELD NOTES**: If you find unrelated bugs/messy code: **DO NOT fix them silently**. Log them in a "Field Notes" section at the end of your response and await instruction.

## 3. Philosophy
*   **Logic > Speed**: Accuracy to the Project Laws is more important than response time.
*   **Sustainability > Speed**: Never choose a "fast hack" if it creates technical debt.
*   **Absolute Honesty**: If a chosen path leads to a mess, **STOP** and report it. Do not try to "code your way out". Revert and rethink.
