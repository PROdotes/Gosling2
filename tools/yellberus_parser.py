"""
Parser for extracting FieldDef entries from yellberus.py using AST.
"""

import ast
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from pathlib import Path


@dataclass
class FieldSpec:
    """Internal representation of a field definition."""
    name: str = ""
    ui_header: str = ""
    db_column: str = ""
    field_type: str = "TEXT"
    id3_tag: Optional[str] = None
    visible: bool = True
    editable: bool = True
    filterable: bool = False
    searchable: bool = False
    required: bool = False
    portable: bool = True
    # Extra properties we track but don't edit in UI
    model_attr: Optional[str] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    min_length: Optional[int] = None
    filter_type: Optional[str] = None
    grouping_function: Optional[str] = None
    extra_attributes: Dict[str, Any] = field(default_factory=dict)


# Default values for FieldDef (fallback if parsing fails)
FIELD_DEFAULTS = {
    "visible": True,
    "editable": True,
    "filterable": False,
    "searchable": False,
    "required": False,
    "portable": True,
    "field_type": "TEXT",
}


def extract_class_defaults(file_path: Path) -> dict:
    """
    Parse yellberus.py to extract the actual default values defined in the FieldDef class.
    Returns a dictionary of {attribute: value}.
    """
    import re
    defaults = FIELD_DEFAULTS.copy()
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Regex to find: class FieldDef: ... (indented fields)
        # We look for lines like "    visible: bool = True" or "    filterable: bool = False"
        # inside the class definition.
        
        # Simple approach: Audit specific known keys
        for key in defaults.keys():
            if key == "field_type": continue # Enum handling is complex, skip for now
            
            # Look for: key : type = Value
            # pattern: visible : bool = False
            pattern = re.compile(rf"\s+{key}\s*:\s*bool\s*=\s*(True|False)")
            match = pattern.search(content)
            if match:
                val_str = match.group(1)
                defaults[key] = (val_str == "True")
                
    except Exception as e:
        print(f"Warning: Could not parse class defaults: {e}")
        
    return defaults


def parse_yellberus(file_path: Path) -> List[FieldSpec]:
    """
    Parse yellberus.py and extract all FieldDef entries from the FIELDS list.
    
    Args:
        file_path: Path to yellberus.py
        
    Returns:
        List of FieldSpec objects representing each field definition.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    tree = ast.parse(source)
    fields = []
    
    # Find the FIELDS assignment (could be Assign or AnnAssign)
    for node in ast.walk(tree):
        target_name = None
        value_node = None
        
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "FIELDS":
                    target_name = "FIELDS"
                    value_node = node.value
                    break
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "FIELDS":
                target_name = "FIELDS"
                value_node = node.value
        
        if target_name == "FIELDS" and isinstance(value_node, ast.List):
            for elem in value_node.elts:
                if isinstance(elem, ast.Call):
                    field_spec = _parse_fielddef_call(elem)
                    if field_spec:
                        fields.append(field_spec)
            break  # Found FIELDS, no need to continue
    
    return fields


def _parse_fielddef_call(call_node: ast.Call) -> Optional[FieldSpec]:
    """Parse a single FieldDef(...) call into a FieldSpec."""
    spec = FieldSpec()
    
    for keyword in call_node.keywords:
        key = keyword.arg
        value = _extract_value(keyword.value)
        
        if key == "name":
            spec.name = value
        elif key == "ui_header":
            spec.ui_header = value
        elif key == "db_column":
            spec.db_column = value
        elif key == "field_type":
            # Handle FieldType.XXX enum
            if isinstance(keyword.value, ast.Attribute):
                spec.field_type = keyword.value.attr
            else:
                spec.field_type = str(value)
        elif key == "visible":
            spec.visible = value
        elif key == "editable":
            spec.editable = value
        elif key == "filterable":
            spec.filterable = value
        elif key == "searchable":
            spec.searchable = value
        elif key == "required":
            spec.required = value
        elif key == "portable":
            spec.portable = value
        elif key == "model_attr":
            spec.model_attr = value
        elif key == "min_value":
            spec.min_value = value
        elif key == "max_value":
            spec.max_value = value
        elif key == "min_length":
            spec.min_length = value
        elif key == "filter_type":
            spec.filter_type = value
        elif key == "grouping_function":
            # Store function name as string
            if isinstance(keyword.value, ast.Name):
                spec.grouping_function = keyword.value.id
        else:
            # Preserve unknown attributes (e.g. query_expression)
            spec.extra_attributes[key] = value
    
    return spec if spec.name else None


def _extract_value(node: ast.expr) -> Any:
    """Extract a Python value from an AST node."""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Name):
        if node.id == "True":
            return True
        elif node.id == "False":
            return False
        elif node.id == "None":
            return None
        return node.id
    elif isinstance(node, ast.Attribute):
        # For things like FieldType.TEXT
        return node.attr
    return None


def parse_field_registry_md(file_path: Path) -> List[FieldSpec]:
    """
    Parse FIELD_REGISTRY.md and extract field data from the Current Fields table.
    
    Args:
        file_path: Path to FIELD_REGISTRY.md
        
    Returns:
        List of FieldSpec objects representing each documented field.
    """
    import re
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    fields = []
    
    # Find the Current Fields table (starts with | Name | UI Header |...)
    in_table = False
    for line in content.split("\n"):
        line = line.strip()
        
        # Skip empty lines and separator lines
        if not line or line.startswith("|---"):
            continue
            
        # Detect table header
        if line.startswith("| Name") and "UI Header" in line:
            in_table = True
            continue
            
        # End of table (next section or empty)
        if in_table and (line.startswith("##") or line.startswith("**Total:")):
            break
            
        # Parse table row
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]  # Remove empty first/last
            if len(parts) >= 11:
                # | Name | UI Header | DB Column | Type | Visible | Editable | Filterable | Searchable | Required | Portable | ID3 Tag |
                name = parts[0].strip("`")
                spec = FieldSpec(
                    name=name,
                    ui_header=parts[1],
                    db_column=parts[2],
                    field_type=parts[3],
                    visible=parts[4] == "Yes",
                    editable=parts[5] == "Yes",
                    filterable=parts[6] == "Yes",
                    searchable=parts[7] == "Yes",
                    required=parts[8] == "Yes",
                    portable=parts[9] == "Yes",
                    id3_tag=parts[10] if parts[10] != "—" else None,
                )
                fields.append(spec)
    
    return fields


if __name__ == "__main__":
    # Quick test
    from pathlib import Path
    yellberus_path = Path(__file__).parent.parent / "src" / "core" / "yellberus.py"
    fields = parse_yellberus(yellberus_path)
    print(f"Parsed {len(fields)} fields from yellberus.py:")
    for f in fields[:5]:
        print(f"  - {f.name}: {f.ui_header} ({f.field_type})")
    
def write_yellberus(file_path: Path, fields: List[FieldSpec], defaults: dict = None) -> bool:
    """
    Update the FIELDS list in yellberus.py with the provided field specifications.
    Also updates the FieldDef class defaults if 'defaults' is provided.
    Preserves the rest of the file using AST to locate the assignment.
    """
    import re
    
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # 1. Update FieldDef class defaults if provided
    # We scan for 'class FieldDef:' and then update specific attributes
    if defaults:
        in_class = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("class FieldDef"):
                in_class = True
                continue
            
            if in_class:
                # Stop if we hit end of class (simple heuristic: unindented line that isn't empty/comment)
                if line and not line[0].isspace() and stripped and not stripped.startswith("#"):
                    in_class = False
                    # Don't break, keep scanning just in case? No, usually fine.
                
                # Check for attributes we want to update
                # pattern: '    visible: bool = True'
                # keys: visible, editable, filterable, searchable, required, portable
                for key, val in defaults.items():
                    # Robust check: key, type hint, assignment (handling spaces)
                    # pattern: key : bool =
                    pattern = re.compile(rf"^\s*{key}\s*:\s*bool\s*=\s*")
                    if pattern.match(line): # Use raw line to match, but we need indentation from it
                        # Preserve indentation
                        match = pattern.match(line)
                        indent = line[:line.find(key)]
                        # OR just use the match start?
                        # line is "    visible: bool = True\n"
                        # stripped is "visible: bool = True"
                        # indentation is line count - len(lstrip)
                        
                        # Simpler: Get indentation
                        indent = line[:len(line) - len(line.lstrip())]
                        
                        # Construct new line
                        lines[i] = f"{indent}{key}: bool = {val}\n"
                        # print(f"DEBUG: Updated {key} default to {val}")

    # 2. Update FIELDS list (AST based replacement)
    source = "".join(lines)
    tree = ast.parse(source)
    
    start_lineno = -1
    end_lineno = -1
    
    # Locate FIELDS assignment
    for node in ast.walk(tree):
        is_target = False
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "FIELDS":
                    is_target = True
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "FIELDS":
                is_target = True
                
        if is_target:
            # Found it!
            start_lineno = node.lineno
            end_lineno = node.end_lineno
            break
            
    if start_lineno == -1:
        print("Error: Could not find FIELDS assignment in yellberus.py")
        return False

    # Determine validation defaults (fallback to FIELD_DEFAULTS if not passed)
    # Be careful: FIELD_DEFAULTS in this file might differ from actual file defaults if we didn't just update them!
    # But 'defaults' arg represents the DESIRED state (which we just wrote to the class).
    # So we should use 'defaults' for sparse logic.
    
    # Defaults map for sparse writing logic
    active_defaults = defaults.copy() if defaults else FIELD_DEFAULTS.copy()
    
    # Handle missing keys simply
    if 'editable' not in active_defaults: active_defaults['editable'] = True # Hardcode failsafes

    # Generate the new list code
    new_code_lines = ["FIELDS: List[FieldDef] = ["]
    
    for f in fields:
        new_code_lines.append("    FieldDef(")
        new_code_lines.append(f'        name="{f.name}",')
        new_code_lines.append(f'        ui_header="{f.ui_header}",')
        new_code_lines.append(f'        db_column="{f.db_column}",')
        
        # Field Type
        if f.field_type == "TEXT":
            if f.field_type != "TEXT": new_code_lines.append(f'        field_type=FieldType.{f.field_type},')
        else:
            new_code_lines.append(f'        field_type=FieldType.{f.field_type},')
            
        new_code_lines.append(f'        visible={f.visible},')
        new_code_lines.append(f'        editable={f.editable},')
        new_code_lines.append(f'        filterable={f.filterable},')
        new_code_lines.append(f'        searchable={f.searchable},')
        new_code_lines.append(f'        required={f.required},')
        new_code_lines.append(f'        portable={f.portable},')
        
        # Preserved fields (that aren't in UI)
        if f.model_attr: new_code_lines.append(f'        model_attr="{f.model_attr}",')
        if f.min_value is not None: new_code_lines.append(f'        min_value={f.min_value},')
        if f.max_value is not None: new_code_lines.append(f'        max_value={f.max_value},')
        if f.min_length is not None: new_code_lines.append(f'        min_length={f.min_length},')

        if f.filter_type: new_code_lines.append(f'        filter_type="{f.filter_type}",')
        if f.grouping_function: new_code_lines.append(f'        grouping_function={f.grouping_function},')
        
        # Write extra preserved attributes
        for k, v in f.extra_attributes.items():
            if isinstance(v, str):
                # Use repr to handle quoting correctly, but maybe strip outer quotes if you want specific style?
                # Actually, repr() adds quotes. Existing code adds quotes manually: name="{f.name}".
                # For safety and ensuring valid python syntax for arbitrary strings:
                new_code_lines.append(f'        {k}={repr(v)},')
            else:
                new_code_lines.append(f'        {k}={v},')
        
        new_code_lines.append("    ),")
        
    new_code_lines.append("]")
    
    # Construct new file content
    # We rely on 'lines' having potentially Updated Defaults from Step 1
    
    final_lines = lines[:start_lineno-1] + [l + "\n" for l in new_code_lines] + lines[end_lineno:]
    
    # Write backup
    bak_path = file_path.with_suffix(".py.bak")
    with open(bak_path, "w", encoding="utf-8") as f:
        f.writelines(lines) # Writes the version BEFORE list update (but AFTER in-memory class update? No, readlines was original)
                            # Wait, lines[i] was modified in-place in Step 1.
                            # So 'lines' contains updated class defaults.
                            # So backup will contain updated class defaults but OLD list?
                            # Ideally backup is PURE original.
                            
                            # Let's re-read original for backup? Or just accept backup is "Pre-Overwrite".
                            # Since we haven't written to disk yet, 'file_path' still has original.
                            # We should copy 'file_path' to 'bak_path' directly before overwriting.
    
    import shutil
    shutil.copy2(file_path, bak_path)

    # Write new file
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(final_lines)
    return True
        
def write_field_registry_md(file_path: Path, fields: List[FieldSpec]) -> bool:
    """
    Update the 'Current Fields' table in FIELD_REGISTRY.md.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    # Find table start and end
    table_start = -1
    table_end = -1
    
    for i, line in enumerate(lines):
        if line.strip().startswith("| Name") and "UI Header" in line:
            table_start = i
            # Skip header and separator
            table_end = i + 2
            continue
            
        if table_start != -1 and i > table_start + 1:
            if not line.strip() or line.startswith("##") or line.startswith("**Total:"):
                table_end = i
                break
            # If we reach EOF, table_end is EOF
            table_end = i + 1
            
    if table_start == -1:
        print("Error: Could not find Current Fields table in FIELD_REGISTRY.md")
        return False
        
    # Generate new table rows
    # Header: | Name | UI Header | DB Column | Type | Visible | Filterable | Searchable | Required | Portable | ID3 Tag |
    # Separator: |---|---|---|...
    
    # We keep lines[:table_start+2] (Header + Separator)
    # Then append new rows
    # Then append lines[table_end:]
    
    new_rows = []
    for f in fields:
        yes_no = lambda x: "Yes" if x else "No"
        id3 = f.id3_tag if f.id3_tag else "—"
        row = f"| `{f.name}` | {f.ui_header} | {f.db_column} | {f.field_type} | {yes_no(f.visible)} | {yes_no(f.editable)} | {yes_no(f.filterable)} | {yes_no(f.searchable)} | {yes_no(f.required)} | {yes_no(f.portable)} | {id3} |"
        new_rows.append(row + "\n")
        
    final_lines = lines[:table_start+2] + new_rows + lines[table_end:]
    
    # Update Total count line if it exists immediately after table
    # Look for "**Total:" line in a few lines after table_end
    for i in range(len(final_lines)):
        if final_lines[i].strip().startswith("**Total:"):
            final_lines[i] = f"**Total: {len(fields)} fields**\n"
            break

    # Write backup
    bak_path = file_path.with_suffix(".md.bak")
    with open(bak_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    # Write new file
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(final_lines)
        
    return True
