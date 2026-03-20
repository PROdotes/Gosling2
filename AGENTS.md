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
4. `black .` and `ruff check . --fix` pass with 0 errors
5. `pytest` passes on the entire test suite
6. `pytest --cov` shows 100% coverage for new code

---

## 7. No Emojis
- Emojis are strictly forbidden in code, configuration files (JSON, etc.), and UI elements.
- Prevents encoding issues and visual "noise" in terminal/IDE.