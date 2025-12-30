# T-55 Execution Plan: The Chip Bay (Visuals)

**Status**: READY
**Objective**: Implement the "Pro Audio HUD" visual style for filter chips.
**Constraint**: NO LOGIC REFACTORING. Only Visuals + Layout Wiring.

## 1. The Inventory (What we touch)

### A. `src/resources/theme.qss`
*   **Action**: Create `#NeonChip` class selector.
*   **Definition**:
    *   Base: `#222` bg, `1px solid #333` border, `#BBB` text.
    *   Radius: `12px` (Pill).
    *   Hover: `#2A2A2A` bg, `1px solid #FF8C00` border, `#FFF` text.
    *   Pressed: Inset shadow style (optional).

### B. `src/presentation/widgets/filter_widget.py`
*   **Action**: Update `_sync_chip_bay` logic.
*   **Task**:
    *   Ensure generated buttons set `setObjectName("NeonChip")`.
    *   Verify `FlowLayout` parameters (spacing `6px`).
    *   Check `ChipBayScroll` margins (`4px` top/bottom).

## 2. The Verification (Checklist)
*   [ ] Chips appear when filters are selected in Tree View.
*   [ ] Chips wrap correctly in the `FlowLayout`.
*   [ ] Hover state triggers subtle orange glow (Border).
*   [ ] Clicking chip removes it (Logic check - already exists, verify visual feedback).
*   [ ] No overlap with Tree View or Header.

## 3. Rollback
*   If visuals break layout: Comment out `#NeonChip` in QSS (revert to default btn).
