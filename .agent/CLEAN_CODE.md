# Clean Code Principles — Quick Reference

## 1. Naming
- Names should reveal intent (`getUserById` not `get`)
- Avoid abbreviations unless universally understood (`id` ok, `usr` not ok)
- Classes = nouns, functions = verbs
- Be consistent (`fetch`/`get`/`retrieve` — pick one)

## 2. Functions
- **Do one thing** (Single Responsibility)
- Keep them small (~20 lines max, ideally <10)
- Few arguments (0-2 ideal, 3 max)
- No side effects (or make them obvious)
- Command/Query separation — either change state OR return data, not both

## 3. Comments
- Code should be self-documenting
- Comments explain *why*, not *what*
- Delete commented-out code
- TODO comments are tech debt markers

## 4. Formatting
- Consistent indentation
- Vertical density = conceptual affinity
- Related code should be close together
- Caller above callee

## 5. DRY (Don't Repeat Yourself)
- If you copy-paste, you're probably doing it wrong
- Extract common logic into functions/classes

3 5 2 1 4 3