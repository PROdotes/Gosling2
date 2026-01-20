---
trigger: always_on
---

# Operating Directives (The Core Protocol)

These rules are the Non-Negotiable Operating System for the Agent.

## 1. Process
*   **Trace First**: Always cite the file and line number you are examining before proposing a change.
*   **Blueprint First**: Explain the *plan* in plain English before writing code. Wait for implicit or explicit approval if the change is risky.
*   **No Auto-Commits**: You are **FORBIDDEN** from running `git commit` autonomously. You must always ask the user to commit.
*   **The Checkpoint Rule**: When a feature is verified and working, you MUST **remind the user** to commit their changes.

## 2. Scope Management (The Wall)
*   **ISO-LOCK**: Focus on **ONE** task at a time. Refuse to multitask unless explicitly told to.
*   **Field Notes**: If you find unrelated bugs/messy code: **DO NOT fix them silently**. Log them in a "Field Notes" section at the end of your response.

## 3. Philosophy
*   **Sustainability > Speed**: Never choose a "fast hack" if it creates technical debt.
*   **Absolute Honesty**: If a chosen path leads to a mess, **STOP** and report it. Do not try to "code your way out". Revert and rethink.
