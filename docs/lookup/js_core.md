# JS Core
*Location: `src/static/js/dashboard/`*

**Responsibility**: Entry point, global state management, and shared logic utilities.

---

## Dashboard Entry Point
*Location: `src/static/js/dashboard/main.js`*

**Responsibility**: Bootstraps the application, manages global search state, and owns the multi-select selection model (checkbox selection + multi-edit entry).

---

## App Constants
*Location: `src/static/js/dashboard/constants.js`*

### PROCESSING_STATUS
Enum for song review state.

---

## Logic Utils
*Location: `src/static/js/dashboard/utils/`*

### parseTagInput(rawInput, rules)
*Location: `src/static/js/dashboard/utils/tag_input.js`*
Splits a raw string into name and category parts.

### renderRoutingPatternHtml(pattern)
*Location: `src/static/js/dashboard/utils/routing_pattern.js`*
Splits a filing routing pattern (`target_path`/`default_rule`) into literal text and `{token}` pieces. Literal segments render as plain escaped text; each token renders as a `.routing-token` chip with a hover title spelling out the substitution ("Replaced with this song's Artist") -- see [[feedback_placeholder_vs_literal_display]] for why humanized plain text alone isn't enough. Used by `orchestrator.js`'s `manageTag` for the Edit Tag modal's genre routing preview. Extracted out of `orchestrator.js` so it's importable in isolation for unit tests (`orchestrator.js` has side-effectful transitive imports that assume the real app DOM).
