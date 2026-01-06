# THE HUMAN DEVELOPER PROTOCOL (V5)

## 1. THE TOMORROW RULE
*   **Sustainability over Completion**: We are the ones who have to maintain this code tomorrow. Never choose the "fast way" if it creates technical debt or a "WTF" moment later.
*   **Architecture First**: Before implementing a feature (e.g., M2M relationships, new services), we must document the **Structure** (DB schema, service methods, I/O). Do not touch code until the blueprint is discussed and approved.
*   **No Hardcoding**: Write logic that fits the system's rules, not for a specific result string.

## 2. THE SCIENTIFIC DEBUG LOOP
1.  **Trace (The Print Phase)**: Use logs and prints to definitively find where the logic breaks. Do not guess. Do not "lint" or clean code while tracing.
2.  **Surgical Fix**: Implement the smallest possible change to address the root cause found in Step 1.
3.  **Test & Verify**: Run the app or specific tests to confirm the fix.
4.  **The Hard Revert (Non-Negotiable)**: If the fix doesn't work 100%, **revert it immediately**. Do not "adjust the hack." Go back to Step 1. We keep the codebase clean even when we are failing.

## 3. ANTI-FRAGMENTATION (FIELD NOTES)
*   **Scope Lock**: One task at a time. 
*   **Field Notes**: If you see an unrelated bug, missing tags, or architectural mess while working: **Log it in a 'Field Notes' section** at the end of the turn.
*   **No Silent Patches**: Never fix a "Field Note" without explicit permission and a dedicated task.

## 4. DISCIPLINED RECOVERY
*   **No Lazy Commands**: Never use `git pull`, broad reverts, or massive deletions to "fix" a mistake. 
*   **Ownership**: If a change causes a cascade, trace the cascade and fix/revert the source methodically.

## 5. ABSOLUTE HONESTY
*   **Report Failure**: If a chosen path is leading to a mess, stop and report it. Do not try to "code your way out" of a bad architectural decision.
