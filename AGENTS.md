# GOSLING2 CONSTITUTION

Project protocols for architectural integrity.

> Assume a technical persona. No fluff, no hand-holding, just the facts.

---

## 1. Spec-First
- Search Open Brain before planning
- Agree on methods, location, and tests before writing code
- Write code only after plan approval
- Non-trivial changes require a spec in `docs/`

---

## 2. Lookup Protocol
- Check `docs/lookup/` before research or changes
- Every entry must have: header, location, responsibility, signatures
- Every method must have a strict Python signature
- Every entry must have a single, definitive file path

---

## 3. Debug Protocol
- No theorizing without evidence
- Reproduce and analyze exact output before patching
- Services and Repositories must log entry/exit

---

## 4. Open Brain
- Stores permanent lessons and workflow preferences via MCP
- Project state belongs in `docs/`, not the Brain
- Use `[GOSLING2]` or `[GLOBAL]` prefixes for brain operations
- Search brain when starting sessions or hitting familiar bugs

---

## 5. Context Health
- Include Step Id at the beginning of every response
- Suggest a fresh chat if step count exceeds 500

---

## 6. Done Protocol
A task is not done until:
1. `docs/lookup/` is accurate to implementation
2. Logger instrumentation is pervasive
3. Zombie code and orphan files are purged
4. `black .`, `ruff check . --fix`, and `pyright` pass with 0 errors (errors mapping to external libraries like `mutagen` without type stubs are exempt)
5. `pytest` passes on the entire test suite
6. `pytest --cov` shows 100% coverage for new code

---

## 7. No Emojis
- Emojis are strictly forbidden in code, configuration files (JSON, etc.), and UI elements.
- Prevents encoding issues and visual "noise" in terminal/IDE.

---

## 8. Execution Protocol
- Convert specs into a discrete checklist (e.g. <200 lines per step).
- Execute exactly one step autonomously (code, format, local test).
- Stop execution entirely and present the diff.
- Wait for explicit user authorization before starting the next step. Do not ask permission inside an approved step.

---

## 9. No Chat Promises
- Vows, rules, or promises made in the chat UI are meaningless because they are lost when a new chat starts.
- Never write "From now on I'll do X" in a conversation.
- If a workflow rule is broken, do not apologize. Immediately document the correction in `AGENTS.md` or Open Brain so it survives the reset.