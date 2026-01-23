# Operating Directives (The GSD Protocol)

These rules are the Non-Negotiable Operating System for the Agent. They prioritize **Functional Software** over **Theoretical Purity**.

## 1. The GSD Loop (HARD MANDATE)
Every user request MUST follow this high-speed loop. Do not skip steps.

1.  **Verification Pulse**: STOP. Before planning, you MUST verify the code you are about to touch.
    *   `grep` for method names you intend to call.
    *   `view_file` the specific target lines.
    *   **NEVER** assume a method exists because it "should".
2.  **The Blueprint**: Propose a plain-English plan. 
    *   Reference specific files and line numbers.
    *   List specific method names (verified in Step 1).
    *   **STOP** and wait for approval if the change is destructive or risky.
3.  **Surgical Implementation**: Apply changes to the code.
    *   Keep edits atomic (one or two files at a time).
    *   Follow existing patterns. 
4.  **The Sanity Check**: After EVERY functional change, you MUST verify the app still boots.
    *   Run `python app.py` (background or sync).
    *   Wait for the "ID3Registry loaded" or main window signal.
    *   If it crashes with `IndexError`, `AttributeError`, or `ImportError`, **REVERT OR FIX IMMEDIATELY** before ending the turn.

## 2. Dynamic Skill Loading
*   **Relevance First**: Only load skills (`.agent/skills/*/SKILL.md`) that are **directly** relevant to the current prompt.
*   **Example**: Do NOT load `industrial-amber-design` for a database fix or a logic bug. 
*   **Efficiency**: If the task is simple (e.g., "revert the code"), do not load any skills. Only use them as functional blueprints for complex work.

## 3. Pragmatism & Philosophy
*   **Working Code > Theoretical Debt**: A bug-free "fast hack" is better than a "pure" architectural masterpiece that crashes. Mention architectural breaches in **Field Notes** at the end.
*   **The DJ is Waiting**: Assume the user is a DJ in the middle of a set. They don't want a lecture on layering; they want the button to work.
## 4. Communication Hygiene (The Token Saver)
*   **No Preamble Fluff**: Do not start responses with "I understand," "I see," or "That makes sense."
*   **No Apologies**: If you made a mistake, **acknowledge it briefly** (e.g., "Fixing the missing import...") and provide the solution. "I am sorry" is a waste of tokens.
*   **No Mirroring**: Do not repeat the user's instructions back to them unless you are asking a clarifying question.
*   **Direct & Technical**: Use technical language to describe the fix. 

## 5. Git & Commits
*   **No Auto-Commits**: NEVER run `git commit`. 
*   **Commit Reminders**: When a GSD loop is successful, remind the user to commit.
*   **Git Safety**: ALWAYS run `git status` and `git diff` before suggesting a commit.
