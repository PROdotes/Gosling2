# JS Core
*Location: `src/static/js/dashboard/`*

**Responsibility**: Entry point, global state management, and shared logic utilities.

---

## Dashboard Entry Point
*Location: `src/static/js/dashboard/main.js`*

**Responsibility**: Bootstraps the application and manages global search state.

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

### validators
*Location: `src/static/js/dashboard/utils/validators.js`*
Object containing metadata validation functions.
