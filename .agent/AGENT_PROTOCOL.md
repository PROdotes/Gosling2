# THE GOSLING PROTOCOL (V6)

## 0. THE HEARTBEAT
*   **Step ID | Pulse**: Mandatory header for tracking.
*   **Step 100**: STOP and re-read this file. Confirm alignment.

---

## 1. THE PARTNER (Blueprint First)
*   **Trace**: Cite File/Line. Explain the current flow FIRST.
*   **Blueprint**: Propose the change. **Wait for EXACT approval before touching code.**
*   **No Hardcoding**: Write logic that fits the system's rules, not for a specific result string.
*   **Statics**: **BAN** inline QSS in `.py`. Use `.qss` files ONLY.

---

## 2. THE WALL (Scope Lock)
*   **ISO-LOCK**: One task at a time. Refuse all others until Test/Commit.
*   **Field Notes**: If you see an unrelated bug, missing tags, or architectural mess: **Log it in a 'Field Notes' section** at the end of the turn. Do NOT silently fix it.
*   **NO NAGGING**: Shut up and wait for the User when asked to pause.

---

## 3. THE SCIENTIFIC DEBUG LOOP
1.  **Trace (The Print Phase)**: Use logs and prints to definitively find where the logic breaks. Do not guess. Do not "lint" or clean code while tracing.
2.  **Surgical Fix**: Implement the smallest possible change to address the root cause found in Step 1.
3.  **Test & Verify**: Run the app or specific tests to confirm the fix.
4.  **The Hard Revert (Non-Negotiable)**: If the fix doesn't work 100%, **revert it immediately**. Do not "adjust the hack." Go back to Step 1.

---

## 4. GIT DISCIPLINE
*   **Local `commit`**: Permitted.
*   **Network Ops (`pull`/`push`)**: **FORBIDDEN** without explicit confirmation.
*   **Destructive `reset`**: **FORBIDDEN** without explicit confirmation.
*   **Receipts**: Show Before/After snippets for every change.

---

## 5. THE TOMORROW RULE
*   **Sustainability over Completion**: We are the ones who have to maintain this code tomorrow. Never choose the "fast way" if it creates technical debt.
*   **Architecture First**: Before implementing a feature (e.g., M2M relationships, new services), document the **Structure** (DB schema, service methods, I/O). Do not touch code until the blueprint is discussed and approved.

---

## 6. ABSOLUTE HONESTY
*   **Report Failure**: If a chosen path is leading to a mess, stop and report it. Do not try to "code your way out" of a bad architectural decision.
