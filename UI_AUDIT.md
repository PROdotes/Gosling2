# UI Design Audit (Dec 27, 2025)

**Status**: Raw Critique
**Scope**: Main Workstation Interface (v0.1.0 Alpha)

## The Good (Keep)
*   **Industrial Aesthetic**: The Amber (`#FF8C00`) on Dark (`#0A0A0A`) palette is strong and professional.
*   **Segmented Layout**: Clear separation of Filter / Library / Editor.
*   **Typography**: "Agency FB" / "Bahnschrift" headers look crisp.

## The Issues (To Fix)

### 1. Header & Frame Alignment
*   [ ] **App Header**: The Settings Icon (Top-Left) and "GOSLING // WORKSTATION" text are vertically misaligned. The gap feels accidental.
*   [ ] **Command Rails**: The "ALL + / ALL -" and "MATCH" buttons float without a solid anchor to the grid below.
*   [ ] **Right Header**: The `[ EDIT MODE ]` toggle and neighbor buttons lack visual cohesion (stuck together widgets).

### 2. Editor Panel (Right)
*   [ ] **The Void**: When "No Selection" is active, the panel is a massive black hole. Needs a "Ghost State" (watermark/logo or instruction).
*   [ ] **Footer Crowding**: The "Discard", "PENDING", and "SAVE" buttons are squeezed.
    *   *Specific*: The "PENDING" text is clipped (`'ENDING`).
    *   *Specific*: Button padding is insufficient for the text size.

### 3. Library Grid
*   [ ] **Column Headers**: "PERFORMER" is cut off as "ERFORMER". Scaling needs tuning.
*   [ ] **Spacing**: Columns feel weirdly spaced relative to content density.

### 4. Player Deck (Footer)
*   [ ] **Visual Balance**: The "NO MEDIA ARMED" text is disproportionately large/loud compared to the rest of the UI.
*   [ ] **Album Art Hole**: The placeholder circle looks like a missing asset/hole.

### 5. Filter Widget (Left)
*   [ ] **Chip Bay**: The chips (Year/Publisher) feel cramped against the bottom footer.

## Action Plan
*   **Ref**: T-60 (Editor Footer Redesign) covers the Right Panel Footer issues.
*   **Ref**: T-53 (UI Polish) can cover the Header/Alignment fixes.
