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
Splits a raw string into name and category parts. (Only file in `utils/` — the old `validators.js` was deleted; validation lives in the backend.)
