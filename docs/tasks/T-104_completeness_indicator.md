# T-104: Completeness Indicator

**Status**: Partially Implemented
**Priority**: Medium
**Complexity**: Low-Medium
**Estimate**: ~2.0h

## 🎯 Goal
Add a dedicated visual column in the main grid showing song completeness at a glance, allowing quick identification of records missing required fields.

## 📊 Current Architecture Support

### ✅ Already Implemented
The backend infrastructure is fully in place:

1. **Validation Logic**: `yellberus.validate_row()` provides comprehensive field validation.
2. **Incompleteness Detection**: `_get_incomplete_fields()` method already exists in the library widget.
3. **Completeness Calculation**: Every row's completeness is calculated during load.
4. **Gating Logic**: The "Done" toggle is disabled when required fields are missing.
5. **Error Messages**: Validation errors are surfaced in dialogs when save is attempted.

### ❌ Missing
- **Visual Column**: No dedicated column with LED/icon showing completeness state.
- **At-a-Glance Status**: Currently, users must attempt to save or hover to discover missing fields.

## 🎨 Proposed UI Design

### Option A: LED Indicator Column
Add a narrow column (similar to Status Deck) with a `GlowLED`:
- 🟢 **Green**: All required fields populated
- 🟡 **Yellow**: Some required fields missing (partial)
- 🔴 **Red**: Critical fields missing (Title, Duration, etc.)

### Option B: Completeness Percentage
Display a small percentage or progress bar:
- `100%` = Complete
- `75%` = Missing some fields
- Tooltip shows which fields are missing

### Option C: Icon-Based
Simple icon in a narrow column:
- ✅ Complete
- ⚠️ Incomplete (with tooltip listing missing fields)

## 🛠️ Implementation Steps

### Phase 1: Backend (~30 min)
1. Add `get_completeness_status(song_id) -> Tuple[Completeness, List[str]]` to `YellberusService`
   - Returns enum (COMPLETE, PARTIAL, CRITICAL) and list of missing field names
2. Ensure this is cached per-row to avoid repeated validation calls

### Phase 2: UI Column (~1.0 h)
1. Add new column "Status" or "✓" to the grid model
2. Create custom delegate that renders `GlowLED` based on completeness
3. Wire tooltip to show missing field names on hover

### Phase 3: Integration (~30 min)
1. Connect to existing refresh logic so indicator updates on edit
2. Ensure column is sortable (complete first/last)
3. Add column to default visible columns

## 📁 Files to Modify
- `src/business/yellberus.py` - Add completeness status method
- `src/presentation/widgets/library_table_model.py` - Add column
- `src/presentation/delegates/` - Add completeness delegate (or reuse LED delegate)
- `src/presentation/widgets/library_widget.py` - Wire up column

## 🔗 Related
- **T-102**: "Show Truncated" Filter (uses same validation logic)
- **T-106**: "Missing Data" Column Filter (complements this feature)
- **Status Deck (T-92)**: Similar LED-based visual indicator pattern
