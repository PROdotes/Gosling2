# Field Editor

> **Tool**: `tools/field_editor.py`  
> **Purpose**: Visual editor for managing field definitions in the Yellberus registry.

## Overview

The Field Editor provides a spreadsheet-like interface for managing all field definitions in `yellberus.py`. It supports editing field properties, viewing advanced metadata, and syncing changes to both code and documentation.

## Columns

| Column | Type | Description |
| :--- | :--- | :--- |
| **Name** | Text | Internal field identifier. Custom SQL fields are shown in **bold italic**. |
| **UI Header** | Text | Display name shown in the application UI. |
| **DB Column** | Text | Database column reference (e.g., `S.Title`, `MS.Source`). |
| **Type** | Dropdown | Data type: TEXT, INTEGER, BOOLEAN, LIST, DURATION, DATETIME. |
| **Strategy** | Dropdown | Filter/grouping behavior: Range Filter, Boolean Toggle, Decade Grouping, First Letter. |
| **Visible** | Checkbox | Registry-level visibility gate (see truth table below). |
| **Edit/Filt/Search/Req/Port** | Checkbox | Boolean flags for editability, filterability, searchability, required status, and ID3 portability. |
| **ID3 Tag** | Text | ID3 frame code for portable fields (e.g., TIT2, TPE1). Disabled when not portable. |
| **Validation** | Read-Only | Cross-field validation groups (e.g., `performers, groups`). |

## Visibility Logic

The registry `visible` flag acts as a **gate**:

- **`visible=False`**: Column is always hidden. User has no control.
- **`visible=True`**: Column is available. User can toggle it on/off in their personal view.

| Registry | User Pref | Result |
|:---------|:----------|:-------|
| ✅ ON | ✅ ON | **Shown** |
| ❌ OFF | ✅ ON | Hidden |
| ✅ ON | ❌ OFF | Hidden |
| ❌ OFF | ❌ OFF | Hidden |
**Key rule**: The Field Editor NEVER touches the Settings Manager. Registry changes don't alter user preferences.

## Visual Indicators

### Color Coding
- **Red background**: Field differs from `yellberus.py` (unsaved change)
- **Blue background**: Field differs from `FIELD_REGISTRY.md` (doc drift)
- **Purple background**: Differs from both
- **Green background**: New field
- **Black/disabled**: N/A (e.g., ID3 Tag when not portable)

### Special Markers
- **Bold Italic**: Field has custom `query_expression` SQL. Hover for full query.

## Sparse Writing

Boolean fields are only written to `yellberus.py` if they differ from the class defaults. This keeps field definitions clean and minimal.

## Validation Groups

The Field Editor provides a read-only view of cross-field validation rules (defined in `VALIDATION_GROUPS`).

- **Column**: `Validation`
- **Logic**: If a field is part of a validation group (e.g., "At least one of [performers, groups] must be present"), the editor displays the rule name and the related fields.
- **Visuals**: This ensures that developers can see the "invisible" constraints linked to a field while editing its individual properties.

## Persistence Stability

The application uses a name-based layout persistence system (`column_layouts`). Unlike index-based systems, this is immune to changes in the Field Registry:
- **Resilience**: Adding a new field in the middle of the registry does **not** shift or break user column arrangements.
- **Identity**: Column visibility and widths are tracked by their internal `name`.
- **Atomic Operations**: All table updates are wrapped in an **Atomic Lifecycle** (Freeze -> Snapshot -> Clear -> Build -> Restore -> Thaw) to prevent layout resets during search or filtering.

## 📝 Change Log (T-19)
- **2025-12-21**: Migrated from index-based keys (`layouts_v2`) to name-based keys (`column_layouts`).
- **2025-12-21**: Implemented Sparse Writing (omitting default booleans) in `yellberus_parser.py` to prevent doc drift.
- **2025-12-21**: Centralized the Save-Before-Clear pattern into `LibraryWidget._populate_table`.
- **2025-12-21**: Verified strict enforcement of `visible=False` from registry to UI.
