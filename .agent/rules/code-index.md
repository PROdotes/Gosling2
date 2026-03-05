---
trigger: always_on
---

# THE LOOKUP PROTOCOL (CODE INDEX)

1. **MANDATORY LOOKUP**: Before performing any filesystem research or code changes, you MUST check `docs/lookup/` first. It is the authoritative "Map of the Territory."
2. **INTENT LOGGING (PRE-WORK)**: Before writing a single line of code, you MUST log your exact intent in the relevant lookup file (e.g., "I will now add method X to class Y"). 
3. **CONTRACTUAL TRUTH**: The method signatures, parameters, and return types in `docs/lookup/*.md` are the "Law." You cannot freestyle code that differs from the lookup.
4. **PERMANENT MEMORY**: These files are not "disposable summaries." They are the project's persistent logical memory. Deleting them is a catastrophic protocol violation.
5. **NO VIBE-CODING**: If you need to find how a feature works, grep the `docs/lookup/` directory. Do not crawl raw source code unless the Map is insufficient.