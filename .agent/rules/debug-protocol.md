---
trigger: always_on
---

# THE DEBUG PROTOCOL (THE "LOG IT FIRST" RULE)

1. **NO BLIND GUESSING**: If you are debugging a complex issue (like a race condition, ghost state, or unexpected UI behavior), stop theorizing architectural failures.
2. **THE 3 DEBUG PRINTS**: Before rewriting any code or suggesting a complex fix, you MUST write at least 3 simple debug lines (using `core.logger` or explicit prints) to verify the State, Event Propagation, and Focus.
3. **PROVE IT FIRST**: Example from GOSLING2 scar: "Is Enter hitting the Main Window?", "What is selected when Enter is pressed?", "Is the Remove button pressed on Enter?" Prove what is happening before fixing what you *think* is happening.
4. **REPRODUCE AND TRACE**: You must run the code with these prints and analyze the exact output before writing patches. Never attempt to simultaneously debug and write the final fix in a single turn. 
5. **AGGRESSIVE INSTRUMENTATION**: Services and Repositories must be instrumented to trace "Entry" (what method was called with what args?) and "Exit" (what was found/failed?). If a log is missing, you cannot debug.
