---
trigger: always_on
---

# THE LOOKUP PROTOCOL (CODE INDEX)

1. **MANDATORY LOOKUP**: Before performing any filesystem research or code changes, you MUST check `docs/lookup/` first. It is the authoritative "Map of the Territory."
2. **INTENT LOGGING (PRE-WORK)**: Before writing a single line of code, you MUST physically write your exact intent into the relevant lookup file.
   - **MANDATORY PHRASE**: The intent MUST begin with the literal string: **"I will now..."**
   - **PLACEMENT**: For a new lookup file or a new phase, the file MUST begin exactly with this string. **DO NOT** insert markdown headers, titles, or comments above the intent.
   - **Proposing intent in chat is NOT sufficient.** The chat is ephemeral; the lookup is the ledger.
3. **CONTRACTUAL TEMPLATE (THE GREP-SYNC)**: Every lookup entry MUST follow the "Golden Template" (see `docs/lookup/CATALOG.md`) to ensure fast grep-ability.
   - **MANDATORY LAYOUT**: Each entry must have: Header (# Component Name), Location (*Location: path*), Responsibility (**Responsibility**: brief explanation), and Signatures (### signature).
   - **SIGNATURES**: Every method must have its strict Python signature.
   - **THE LAW**: Simple text descriptions are not code. The signature is the "Law" for implementation.
   - **VIOLATION**: Using vague descriptions (e.g., `GET /api/songs`) or HTTP-verb-only headers INSTEAD of a strict Python signature.
4. **LOCATION DEFINITION**: Every entry MUST have a single, definitive file path.
   - **VIOLATION**: Wildcards (e.g., `src/engine/*.py`) or "Or similar location" are Protocol Violations.
5. **PERMANENT MEMORY**: These files are not summaries. They are the project's persistent logical memory.
6. **NO VIBE-CODING**: Do not crawl raw source code if a lookup entry exists.
7. **THE "ORANGE WALL" AUDIT**: If you violate rules 2, 3, or 4, you have failed. Any attempt to write to `src/` before the Lookup is Approved by the USER is a project-ending Hallucination.