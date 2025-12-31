## 🚧 Pending Work (From .agent/today.md)
* [ ] **Geometry Refactor**: Clean up the "Magic Numbers" (950, 1250, 300) introduced in `album_manager_dialog.py`.
* [ ] **T-46 Polish**: Resolve the "tiny jitter" in footer buttons during expansion.
* [ ] **GlowButton Analysis**: Verify if QSS sizing correctly propagates to the internal `QPushButton`.

## 🗂️ Metadata Editor Friction Points

### 1. "Hidden" Web Search (The "WEB" Button)
**The Issue:** Users (like your boss) feel stuck when a field like **Composers** is empty, missing the connection that the "WEB" button at the bottom can solve the problem for them. It lacks contextual "affinity."

**Proposed "Low-Impact/High-Intuition" Fixes:**
* [ ] **Labeling Change:** Rename `WEB` to `TAGS 🔍` or `FIND DATA`.
* [ ] **Field-Level Trigger:** Add a tiny, subtle search magnifying glass icon *directly* inside or next to the Composers line edit when it's empty.
* [ ] **Empty State Hint:** If a required field is empty, show a ghosted placeholder like `Click WEB below to lookup...` or similar.
* [ ] **Visual Linking:** When hovering over the Web button, briefly highlight the fields it can populate (e.g., Composer, Publisher, Year) with a subtle amber pulse.

### 2. Managed Field Editing (Publisher Jump)
**The Issue:** Boss tried to edit Publisher directly by clicking the label. Since it's an Album property (not Song), it's currently "locked" and unintuitive in the Side Panel.

**Proposed Ideas:**
* [ ] **Interactive Label:** Turn "Publisher" label into a link. Clicking opens a menu: "Edit via [Album A]", "Edit via [Album B]".
* [ ] **Jump Badge:** A small icon inside the Publisher field that opens the Album Manager filtered to that specific album.
* [ ] **Ghost Editing:** Allow typing directly in the field, then show a confirmation: "This updates the publisher for all songs on [Album Name]. Proceed?"

---
