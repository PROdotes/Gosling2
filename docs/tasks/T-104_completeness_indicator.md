# T-104: Completeness Indicator (The Traffic Light Deck)

**Status**: Spec Defined
**Priority**: Medium
**Complexity**: Medium

## 🎯 Goal
Eliminate "Hidden Errors" by repurposing the existing Status Deck (LED) to indicate Metadata Health via color, while preserving File Type info via shape.

## 🚦 The Traffic Light Logic

We replace the existing "Asset Type" color logic with a stricter "Health Status" logic.

### 1. The Color Spectrum (Health)
Priority Order (Top Breakdown overrides lower states):

| Priority | State | Color | Meaning |
| :--- | :--- | :--- | :--- |
| **1** | **DIRTY** | **Magenta** (`#FF00FF`) | Unsaved changes in memory. |
| **2** | **INVALID** | **Red** (`#FF4444`) | Missing REQUIRED fields (Title, Artist, etc.). |
| **3** | **UNPROCESSED** | **Tele-Green** (`#00E5FF`) | Valid data, but has `TXXX:Status=Unprocessed` tag. |
| **4** | **READY** | **Amber** (`#FFC66D`) | Valid, Processed, Ready for Air. |

### 2. The Shape System (File Container)
Orthogonal to color. Tells you "What/Where is this file?"

| Shape | Meaning | Context |
| :--- | :--- | :--- |
| **Square** | **Virtual (VFS)** | File resides inside a ZIP/archive. |
| **Triangle** | **Raw / WAV** | Uncompressed source file (needs conversion). |
| **Circle** | **Standard** | Standard MP3/AAC file on disk. |

### 3. Examples
*   **Red Square**: A file inside a ZIP that is missing its Artist tag.
*   **Green Triangle**: A WAV file that has data but hasn't been marked "Done" (Unprocessed).
*   **Amber Circle**: A perfect MP3, ready to broadcast.

## 🛠️ Implementation Plan

### Phase 1: Logic (Yellberus)
*   Add `get_health_status(row_data) -> Enum` to Yellberus.
*   Must check:
    1.  `yellberus.validate_row()` (Invalid check)
    2.  `TXXX:Status` tag presence (Unprocessed check)

### Phase 2: data Persistence (Model)
*   Do NOT calculate in `paint()`.
*   Calculate Health State at:
    *   **Import/Load**
    *   **Edit (setData)**
*   Store result in `Active` Column (Index 0) user data role (e.g. `UserRole + 1`).

### Phase 3: Rendering (Delegate)
*   Update `_draw_status_deck` in `library_delegate.py`.
*   Implement the Priority Color switch.
*   Preserve existing Shape logic.

