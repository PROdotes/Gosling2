# Field Registry Editor — Design Spec

> **Tool Location**: `tools/field_editor.py`  
> **Purpose**: Unified editor for Yellberus field definitions. Keeps code and documentation in sync.

---

## 🎯 Goals

1. **View all fields** from `yellberus.py` in an editable table.
2. **Add new fields** without manually editing Python.
3. **Export to Markdown** → regenerate `docs/FIELD_REGISTRY.md`.
4. **Write to Yellberus** → regenerate the `FIELDS` list in `yellberus.py` (with backup).
5. **Detect discrepancies** between code and documentation (highlight mismatches).
6. **Safe by default** → backup files before any write operation.

---

## 🚫 Non-Goals (v0.1)

- Database schema migration (separate concern).
- ID3 frame mapping editor (future).
- Undo/redo within the editor (use backups instead).

---

## 📐 UI Design

### Main Window Layout

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  Field Registry Editor                                                        [×]   │
├──────────────────────────────────────────────────────────────────────────────────────┤
│  [Load from Code]                                                                    │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Defaults (applied to new fields) ────────────────────────────────────────────────┐│
│ │ [✓] visible  [✓] editable  [ ] filterable  [ ] searchable  [ ] required  [✓] port ││
│ └────────────────────────────────────────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Fields ───────────────────────────────────────────────────────────────────────────┐│
│ │ Name (Expand) │ Header | DB | Type | Boolean (Fixed 50px) | ID3 Tag (150px) | Valid ││
│ ├───────────────┼────────┼────┼──────┼──────────────────────┼─────────────────┼───────┤│
│ │ performers    │ Perf.. │ .. │ LIST │ ✓  ✓  ✓  ✓     ✓    │ TXXX:performer  │       ││
│ │ pikachu       │ Pikac..│ .. │ TEXT │ ✓  ✓  ✓  ✓     ✓    │ TXXX:pikachu    │       ││
│ └────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│ [+ Add Field]  [Delete Selected]                                      [Save All]    │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ Status: 17 fields. 1 changed from code, 2 differ from MD                            │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### PyQt6 Widgets Required

| Widget | Purpose |
|--------|---------|
| `QMainWindow` | Main application window. |
| `QTableWidget` | Fields table with editable cells. |
| `QCheckBox` | Boolean properties (visible, filterable, etc). |
| `QComboBox` | Type selector (TEXT, INTEGER, LIST, BOOLEAN, DURATION). |
| `QLineEdit` | Text fields (name, header, db_column). |
| `QPushButton` | Actions (Load, Save, Add, Delete). |
| `QMessageBox` | Confirmation dialogs ("Are you sure?"). |
| `QStatusBar` | Status messages (loaded count, pending changes). |

### Cell Color Coding (Real-Time Diff)

Instead of a separate diff dialog, cells are color-coded based on their state:

| Cell State | Background Color | Meaning |
|------------|------------------|---------|
| **Matches both files** | Gray (default) | No changes needed. |
| **Differs from `yellberus.py`** | Soft Red (#3a2020) | Code will be updated on save. |
| **Differs from `FIELD_REGISTRY.md`** | Soft Blue (#20203a) | Docs will be updated on save. |
| **Differs from both** | Soft Purple (#3a2040) | Both files will be updated. |
| **New field (not in either)** | Soft Green (#203a20) | Adding to both. |
| **Disabled/N/A** | Dark (#1a1a1a) | Cell is not applicable (e.g., ID3 Tag when `portable=False`). |

**ID3 Tag Column Behavior:**
- **Read-Only**: The cell is non-editable. Value is always derived from `id3_frames.json`.
- **Lookup**: On load (or when `portable` is toggled ON), the editor looks up the ID3 frame code by matching `field` property in the JSON.
- **Persistence**: The tag value remains visible even when `portable=False`. This indicates to the user that a mapping exists in JSON.
- **Styling**: When `portable=False`, the cell is styled as **disabled** (dark background) but still shows the tag.
- **Missing Mapping Popup**: If `portable=True` but no mapping is found in JSON, on Save a popup appears:
  
  ```
  Title: Missing ID3 Mapping
  
  Field "{field_name}" is portable but has no ID3 mapping.
  
  Should the editor add TXXX:{field_name} for you?
  
  • Yes: Adds the entry to id3_frames.json and continues save.
  • No: Cancels save. You'll need to edit the JSON manually.
  
  [Yes]  [No]
  ```
  
  - **Yes**: Editor adds `"TXXX:{field_name}": {"field": "{field_name}", "type": "text"}` to JSON, then continues save.
  - **No**: Save is aborted. User must edit `id3_frames.json` manually before retrying.

- **Source of Truth**: `id3_frames.json` is authoritative. The popup provides a convenient way to add TXXX entries without manual editing.

**Missing DB Column Popup**: If a field has no `db_column` defined, on Save a popup appears:

  ```
  Title: Missing Database Columns
  
  The following fields have no Database Column defined:
  {field_names}
  
  Should the editor generate default column names?
  
  • Yes: Sets columns to S.{field_name} (e.g., S.pikachu)
  • No: Cancels save. You'll need to enter columns manually.
  
  [Yes]  [No]
  ```
  
  - **Yes**: Editor sets `db_column` to `S.{field_name}` for each missing field, then continues save.
  - **No**: Save is aborted. User must enter column names manually.

**On Save Behavior:**
- Validates DB columns first (blocking or auto-generate)
- Validates ID3 tags next (blocking or auto-add TXXX)
- Saves directly to both `yellberus.py` and `FIELD_REGISTRY.md`.
- *(Note: A pre-save summary dialog was considered but omitted for cleaner UX.)*

### Window Behavior

| Action                      | Behavior                                    |
| :-------------------------- | :------------------------------------------ |
| **Close with unsaved changes** | Prompt: "Save & Close", "Discard", "Cancel". |
| **Delete with unsaved changes** | Allowed (deletion is its own operation). |
| **Load from Code** | Warns if unsaved changes would be lost. |

### Defaults Behavior

The "Defaults" row represents the `FieldDef` class attributes in `yellberus.py`.

1. **Source of Truth**: 
   - Parsed dynamically from `class FieldDef` in `yellberus.py`.
   - NOT hardcoded.

2. **Usage**:
   - **New Fields**: Initialized with these values.
   - **Sparse Writing**: Attributes matching defaults are OMITTED from `yellberus.py` to keep it clean.

3. **Changing Defaults**:
   - Updates `class FieldDef` definition on Save.
   - Does NOT change values of existing fields in memory/UI.
   - Affects how fields are parsed on next reload (omitted values inherit new defaults).

---

## 📁 Files Involved

| File | Read | Write |
|------|------|-------|
| `src/core/yellberus.py` | ✅ Parse FIELDS list | ✅ Regenerate FIELDS block |
| `docs/FIELD_REGISTRY.md` | ✅ (for comparison) | ✅ Regenerate table |
| `tools/field_editor.py` | — | — (the tool itself) |
| `*.backup` | — | ✅ Created before each write |

---

## 🔧 Data Model (Internal)

```python
@dataclass
class FieldSpec:
    name: str
    ui_header: str
    db_column: str
    field_type: str  # TEXT, INTEGER, LIST, BOOLEAN, DURATION
    id3_tag: Optional[str] = None
    visible: bool = True
    editable: bool = True
    filterable: bool = False
    searchable: bool = False
    required: bool = False
    portable: bool = True
```

---

## 🎛️ Defaults Handling

`FieldDef` in `yellberus.py` has built-in defaults. The editor must respect these:

| Property | Default | Notes |
|----------|---------|-------|
| `visible` | `True` | Most fields are visible. |
| `editable` | `True` | Most fields are editable. |
| `filterable` | `False` | Opt-in for filter tree. |
| `searchable` | `False` | Opt-in for global search. |
| `required` | `False` | Opt-in for "Done" validation. |
| `portable` | `True` | Most fields sync to ID3. |

**Rules:**
1.  **On Read**: If a property is missing from the Python code, assume it has the `yellberus.py` class default value.
2.  **On Write**: 
    - **Update Class Defaults**: If UI defaults differ from original class defaults, update the `FieldDef` class definition in `yellberus.py` (respecting AST/architectural constraints).
    - **Update List**: Only emit properties that **differ** from the *NEW* class defaults. Keep output minimal.
3.  **On Add New Field**: Pre-populate the row with the current UI defaults.

**Example:**
```python
# In yellberus.py, this field only specifies non-defaults:
FieldDef(
    name="isrc",
    ui_header="ISRC",
    db_column="S.ISRC",
    visible=False,  # Differs from default (True)
)
# The editor knows: filterable=False, searchable=False, etc. are implicit.
```

---

## 🔄 Workflows

### 1. Load from Code
1. Parse `yellberus.py` using AST or regex.
2. Extract each `FieldDef(...)` block.
3. Populate the table.

### 2. Add New Field
1. User clicks [+ Add Field].
2. New row appears with defaults.
3. User edits values in table.

### 3. Save to MD
1. Iterate over table rows.
2. Generate markdown table string.
3. Write to `docs/FIELD_REGISTRY.md` (replace "Current Fields" section).

### 4. Copy Python Snippet
1. For each row marked `planned` or modified:
2. Generate `FieldDef(...)` Python code.
3. Copy to clipboard (user manually pastes into `yellberus.py`).

---

## ⚠️ Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Regex parsing breaks on code changes | Use Python AST for parsing, not regex. |
| Bad MD generation | Preview before save. Keep backup. |
| User forgets to paste Python | Show clear warning: "Code not updated!" |
| Field type mismatch | Validate against FieldType enum. |

---

## 📋 Progress Checklist (Incremental Build)

### Phase 1: Window Shell
- [ ] **1.1** Create `tools/field_editor.py` with empty `QMainWindow`.
- [ ] **1.2** TEST: Run script, verify window opens and closes cleanly.
- [ ] **1.3** Add toolbar with placeholder buttons (Load, Save).
- [ ] **1.4** TEST: Click buttons, verify no crash (buttons do nothing yet).
- [ ] **1.5** Add status bar at bottom.
- [ ] **1.6** TEST: Verify status bar shows placeholder text.

### Phase 2: Tables
- [ ] **2.1** Add empty Defaults table (header row only).
- [ ] **2.2** TEST: Verify Defaults table renders with correct columns.
- [ ] **2.3** Add empty Fields table (header row only).
- [ ] **2.4** TEST: Verify Fields table renders with correct columns.
- [ ] **2.5** Add "Add Field" and "Delete Selected" buttons below Fields table.
- [ ] **2.6** TEST: Click buttons, verify no crash.

### Phase 3: Load from Code (Read-Only)
- [ ] **3.1** Implement `parse_yellberus()` using AST.
- [ ] **3.2** UNIT TEST: `test_parse_yellberus()` extracts all 15 fields correctly.
- [ ] **3.3** Wire "Load from Code" button to populate Fields table.
- [ ] **3.4** TEST: Click Load, verify table shows all 15 fields with correct values.
- [ ] **3.5** Populate Defaults table from `FieldDef` class defaults.
- [ ] **3.6** TEST: Verify Defaults table shows correct default values.

### Phase 4: Editing (No Save Yet)
- [ ] **4.1** Make string cells editable (double-click to edit).
- [ ] **4.2** TEST: Edit a cell, verify value changes in table.
- [ ] **4.3** Add checkbox widgets for boolean columns.
- [ ] **4.4** TEST: Toggle checkbox, verify state changes.
- [ ] **4.5** Add dropdown for Type column.
- [ ] **4.6** TEST: Change dropdown, verify value updates.
- [ ] **4.7** Implement "Add Field" → new row with defaults.
- [ ] **4.8** TEST: Add field, verify row appears with correct defaults.
- [ ] **4.9** Implement "Delete Selected" with confirmation dialog.
- [ ] **4.10** TEST: Delete a row, verify confirmation appears and row is removed.

### Phase 5: Color Coding
- [ ] **5.1** Parse `FIELD_REGISTRY.md` to get doc values.
- [ ] **5.2** UNIT TEST: `test_parse_field_registry_md()` extracts table correctly.
- [ ] **5.3** Implement cell color coding (compare table vs code vs docs).
- [ ] **5.4** TEST: Edit a cell, verify it changes color.
- [ ] **5.5** Update status bar with change counts.
- [ ] **5.6** TEST: Verify status bar shows correct counts.
- [ ] **5.7** Connect Defaults table to `onChange` → recompute all cell colors.
- [ ] **5.8** TEST: Change a default, verify all affected cells recolor.

### Phase 6: Save to MD
- [ ] **6.1** Implement `generate_md_table()`.
- [ ] **6.2** UNIT TEST: `test_generate_md_table()` produces valid markdown.
- [ ] **6.3** Implement backup creation before write.
- [ ] **6.4** TEST: Save, verify `.backup` file created.
- [ ] **6.5** Wire "Save All" to write `FIELD_REGISTRY.md`.
- [ ] **6.6** TEST: Save, verify MD file updated correctly.

### Phase 7: Save to Yellberus
- [ ] **7.1** Implement `generate_python_fields_block()`.
- [ ] **7.2** UNIT TEST: `test_generate_python_block()` produces valid Python.
- [ ] **7.3** Implement AST-based replacement of FIELDS list in yellberus.py.
- [ ] **7.4** TEST: Save, verify yellberus.py updated correctly.
- [ ] **7.5** Run `pytest` after save → all 357 tests pass.
- [ ] **7.6** TEST: Load again after save → roundtrip produces identical data.

### Phase 8: Validation & Polish
- [ ] **8.1** Implement `name` → `db_column` auto-lookup.
- [ ] **8.2** TEST: Type name, verify db_column auto-populates.
- [ ] **8.3** Implement `name` → `ui_header` auto-suggestion.
- [ ] **8.4** TEST: Type name, verify ui_header auto-populates.
- [ ] **8.5** Implement ID3 tag warning (portable but not in JSON).
- [ ] **8.6** TEST: Set portable=True with unknown tag, verify warning appears.
- [ ] **8.7** Implement "unsaved changes" warning on close.
- [ ] **8.8** TEST: Edit, try to close, verify prompt appears.

### Phase 9: Final Integration
- [ ] **9.1** Add `album`, `publisher`, `genre` using the tool.
- [ ] **9.2** Save to both files.
- [ ] **9.3** Run `pytest` → all tests pass.
- [ ] **9.4** Verify new fields appear in Gosling2 app.
- [ ] **9.5** Document any issues found.
- [ ] **9.6** DONE! 🎉

---

## 🧪 Testing Requirements (Non-Negotiable)

Before this tool touches production files:

1. **Unit Tests**
   - `test_parse_yellberus()` — Correctly extracts all 15 current fields.
   - `test_generate_md_table()` — Output matches expected markdown format.
   - `test_generate_python_block()` — Output is valid Python syntax.
   - `test_roundtrip()` — Parse → Edit → Save → Parse again = identical data.

2. **Integration Tests**
   - Load real `yellberus.py`, modify one field, save, run `pytest` → all 357 tests pass.
   - Add a new field via UI, save, verify it appears in both MD and PY.

3. **Safety Tests**
   - Backup file is created before every write.
   - If write fails mid-operation, original file is intact.
   - Malformed input (empty name, invalid type) is rejected with clear error.

4. **Manual QA**
   - User reviews diff before confirming write.
   - "Are you sure?" dialog on destructive operations.

### Input Validation

| Field | Validation |
|-------|------------|
| `name` | Required. Must be valid Python identifier. On change, triggers `db_column` auto-lookup. |
| `db_column` | Required. **Auto-populated** by matching `name` to known schema columns (e.g., `notes` → `MS.Notes`). User can override. |
| `ui_header` | Required. Non-empty string. Auto-suggested as Title Case of `name` (e.g., `notes` → `Notes`). |
| `id3_tag` | Optional. If `portable=True` and tag not in `id3_frames.json`, show warning info box. |
| `field_type` | Required. Dropdown populated from `FieldType` enum. |

---

## 🚀 Future Enhancements (v0.2+)

- Auto-write to `yellberus.py` with backup.
- Drift detection (compare code vs MD).
- ID3 frame mapping editor.
- Database migration script generator.
