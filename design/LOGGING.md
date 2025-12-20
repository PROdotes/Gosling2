
# Logging & Integrity System

> **Source**: `src/core/logger.py`  
> **Registry**: `src/core/yellberus.py`

## 🎯 Philosophy
We prefer **Loud Runtime Warnings** over silent failures.
If the system detects drift, missing data, or schema issues, it communicates this clearly:
1.  To the **Developer** via console logs (prefixed).
2.  To the **User** via UI feedback (via subscription).

## 🛠️ Unified Logger
We use a centralized singleton logger (`src/core/logger.py`) to avoid ad-hoc `print()` statements.

### Channels

1.  **Console (`sys.stdout`)**:
    *   **Level**: `INFO` and above.
    *   **Format**: Clean, time-stamped messages.
    *   **Purpose**: Immediate feedback during development/use.

2.  **Log File (`gosling.log`)**:
    *   **Level**: `DEBUG` and above.
    *   **Format**: Detailed, including timestamps and levels.
    *   **Location**: Application root.
    *   **Purpose**: Post-mortem debugging and full history.

## 🚦 Warning Roles

We distinguish between two critical types of warnings to reduce noise:

| Type | Function | Prefix | Audience | Example |
|------|----------|--------|----------|---------|
| **Developer** | `logger.dev_warning(msg)` | `🔧 [DEV]` | You (The Coder) | Schema drift, orphaned DB columns, deprecated logic. |
| **User** | `logger.user_warning(msg)` | `⚠️ [USER]` | The End User | Missing files, unknown ID3 tags, invalid configuration. |

### Usage
```python
from src.core import logger

# Developer Warning (e.g. Integrity Check)
logger.dev_warning("Schema mismatch: 'Groups' column found in DB but not Yellberus.")

# User Warning (e.g. Data Import)
logger.user_warning("Could not read tag 'TXXX' from file.")
```

## 🔌 UI Integration (Observer Pattern)

The UI can subscribe to **User Warnings** to display them (e.g., in a Status Bar or Toast). This bridges the gap between Core Logic and Presentation.

```python
# In MainWindow or AppController
from src.core import logger

def on_user_warning(msg: str):
    self.status_bar.showMessage(f"Warning: {msg}", 5000)

logger.subscribe_to_user_warnings(on_user_warning)
```

## 🐕‍🦺 Yellberus Integration
The Field Registry (`yellberus.py`) automatically checks database integrity at startup. It uses `dev_warning` to report any **Orphan Columns** (columns in DB but not in Registry) or mismatches.

This ensures that while the test suite (Layer 1) catches drift in CI, the Runtime Logger catches drift during development sessions.
