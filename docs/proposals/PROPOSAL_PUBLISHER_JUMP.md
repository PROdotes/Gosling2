# PROPOSAL: Managed Field Editing & Publisher Jump (T-83)

## 📌 The Problem
"Managed" fields (like Publisher, which belongs to an Album entity, not a Song entity) are currently read-only in the Side Panel. Users instinctively try to click them to edit, but are met with a "locked" experience.

## 🎯 Objective
Create a seamless bridge between Song-level editing and Album-level metadata management.

## 🛠️ Proposed Solutions

### 1. Interactive Labels (The "Link" Pattern)
- Turn the `Publisher` label into a clickable link.
- **Action**: Clicking opens a small context menu:
  - `Edit [Publisher Name] via Album Manager...`
  - `Change Album...`

### 2. The Jump Badge
- Place a small "External Link" icon (jump badge) inside the Publisher field.
- **Action**: Opens the `AlbumManagerDialog`, auto-selects the current album, and immediately shows the Publisher Sidecar.

### 3. Ghost Editing (Advanced UX)
- Allow the user to type in the "locked" field.
- **Action**: On Tab/Enter, show a confirmation dialog:
  - *"This updates the Publisher for ALL songs on this album ([Album Name]). Proceed?"*
  - This preserves the relational integrity while allowing the "lie" of flat editing.

## 📈 Success Criteria
- Editing an album property from the song view feels frictionless.
- Users no longer feel "stuck" when they see a typo in a locked field.
