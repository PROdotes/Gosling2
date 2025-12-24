"""
Parser for extracting FieldDef entries from yellberus.py using AST.
"""

import ast
from dataclasses import dataclass, field, make_dataclass
from typing import List, Optional, Any, Dict
from pathlib import Path


def extract_class_defaults(file_path: Path) -> dict:
    """
    Parse yellberus.py to extract the actual default values defined in the FieldDef class.
    Returns a dictionary of {attribute: value}.
    """
    import re
    defaults = {}
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Parse the file to find the class definition
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "FieldDef":
                # Iterate over class attributes
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                         # Found a typed attribute: name: str = default
                         attr_name = item.target.id
                         
                         # Check if it has a default value (item.value)
                         if item.value:
                             val = _extract_value(item.value)
                             if val is not None:
                                 defaults[attr_name] = val
                         else:
                             # No default value provided
                             pass
    except Exception as e:
        print(f"Warning: Could not parse class defaults: {e}")
        
    return defaults

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
        # For things like FieldType.TEXT -> "TEXT"
        return node.attr
    return None

def parse_yellberus(file_path: Path) -> List[Any]:
    """
    Parse yellberus.py and extract all FieldDef entries from the FIELDS list.
    
    Args:
        file_path: Path to yellberus.py
        
    Returns:
        List of objects representing each field definition.
    """
    # Extract defaults from class definition
    dynamic_defaults = extract_class_defaults(file_path)
    
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    tree = ast.parse(source)
    fields = []
    
    # Simple dict-based object approach for flexibility
    
    # Find the FIELDS assignment
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
                    field_obj = _parse_fielddef_call(elem, defaults=dynamic_defaults)
                    if field_obj:
                        fields.append(field_obj)
            break
    
    return fields


@dataclass
class DynamicFieldSpec:
    """
    A flexible container that behaves like the FieldSpec but supports arbitrary attributes.
    """
    name: str
    ui_header: str
    db_column: str
    _attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __getattr__(self, name):
        if name in self._attributes:
            return self._attributes[name]
        raise AttributeError(f"'DynamicFieldSpec' object has no attribute '{name}'")
        
    def __setattr__(self, name, value):
        if name in ["name", "ui_header", "db_column", "_attributes"]:
            super().__setattr__(name, value)
        else:
            self._attributes[name] = value

    def get(self, name, default=None):
        return self._attributes.get(name, default)


def _parse_fielddef_call(call_node: ast.Call, defaults: Dict[str, Any] = None) -> Optional[DynamicFieldSpec]:
    """
    Parse a single FieldDef(...) call into a DynamicFieldSpec.
    """
    # 1. Start with defaults
    attributes = defaults.copy() if defaults else {}
    
    # 2. Merge keywords from the call (overriding defaults)
    for keyword in call_node.keywords:
        key = keyword.arg
        value = _extract_value(keyword.value)
        attributes[key] = value
            
    # 3. Extract mandatory fields (falling back to empty string if not in defaults or keywords)
    name = attributes.get("name", "")
    ui_header = attributes.get("ui_header", "")
    db_column = attributes.get("db_column", "")
            
    if not name:
        return None
    
    # 4. Create Spec
    spec = DynamicFieldSpec(name, ui_header, db_column)
    
    # 5. Set attributes (this is now safe because attributes contains the merged correct values)
    # Note: DynamicFieldSpec.__setattr__ handles name/ui_header/db_column specially but correctly
    for k, v in attributes.items():
        setattr(spec, k, v)
        
    return spec


def parse_field_registry_md(file_path: Path) -> List[DynamicFieldSpec]:
    """
    Parse FIELD_REGISTRY.md.
    Note: MD is inherently lossy compared to the Python code (doesn't show all attributes).
    We reconstruct what we can.
    """
    import re
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    fields = []
    
    in_table = False
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("|---"): continue
            
        if line.startswith("| Name") and "UI Header" in line:
            in_table = True
            continue
            
        if in_table and (line.startswith("##") or line.startswith("**Total:")):
            break
            
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 12:
                name = parts[0].strip("`")
                ui_header = parts[1]
                db_column = parts[2]
                
                spec = DynamicFieldSpec(name, ui_header, db_column)
                
                # Recover known columns
                spec.field_type = parts[3]
                
                strategy_str = parts[4].strip()
                strategy = "list"
                if "Range" in strategy_str: strategy = "range"
                elif "Boolean" in strategy_str: strategy = "boolean"
                elif "Decade" in strategy_str: strategy = "decade_grouper"
                elif "First" in strategy_str: strategy = "first_letter_grouper"
                spec.strategy = strategy
                
                spec.visible = parts[5] == "Yes"
                spec.editable = parts[6] == "Yes"
                spec.filterable = parts[7] == "Yes"
                spec.searchable = parts[8] == "Yes"
                spec.required = parts[9] == "Yes"
                spec.portable = parts[10] == "Yes"
                
                # Recover ID3 Tag if present
                if len(parts) > 11:
                    val = parts[11].strip()
                    spec.id3_tag = val if val != "—" else ""
                
                fields.append(spec)
    
    return fields


def write_yellberus(file_path: Path, fields: List[DynamicFieldSpec], defaults: dict = None) -> bool:
    """
    Update the FIELDS list in yellberus.py.
    """
    import re
    
    # 1. Update Class Defaults
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    if defaults:
        # Dynamic update of class attributes
        # Find class FieldDef
        class_start = -1
        class_end = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith("class FieldDef"):
                class_start = i
                continue
            if class_start != -1 and not line[0].isspace() and line.strip() and not line.strip().startswith("#"):
                 # Left indentation block
                 pass # Actually complex to parse end of class strictly by line
        
        # Simple regex update for known keys that exist in defaults
        for key, val in defaults.items():
             pattern = re.compile(rf"^\s*{key}\s*:\s*bool\s*=\s*")
             for i, line in enumerate(lines):
                 if pattern.match(line):
                     indent = line[:len(line) - len(line.lstrip())]
                     lines[i] = f"{indent}{key}: bool = {val}\n"

    # 2. Write Fields List
    # We ignore the `defaults` argument for sparse writing and instead use the 
    # CURRENT defaults extracted from the class (or the updated ones).
    # This ensures we don't assume hardcoded defaults.
    
    # Re-extract defaults from the (potentially updated) lines?
    # Or just use the passed defaults if present?
    # Let's trust the passed defaults if provided, otherwise re-read.
    active_defaults = defaults.copy() if defaults else extract_class_defaults(file_path)

    new_code_lines = ["FIELDS: List[FieldDef] = ["]
    
    for f in fields:
        new_code_lines.append("    FieldDef(")
        new_code_lines.append(f"        name={repr(f.name)},")
        new_code_lines.append(f"        ui_header={repr(f.ui_header)},")
        new_code_lines.append(f"        db_column={repr(f.db_column)},")
        
        # Determine all attributes to write
        # We iterate over the object's stored attributes
        all_attrs = f._attributes.copy()
        
        # Handle field_type specially
        if "field_type" in all_attrs:
            ft = all_attrs.pop("field_type")
            if ft != "TEXT": # TEXT is standard default
                 new_code_lines.append(f'        field_type=FieldType.{ft},')
        
        # Sort keys for deterministic output
        for key in sorted(all_attrs.keys()):
            val = all_attrs[key]
            
            # Check against default
            default_val = active_defaults.get(key)
            
            # Sparse write: only if different from default
            if val != default_val:
                if isinstance(val, str):
                    # Check if it looks like an expression or simple string
                    if key == "query_expression":
                         new_code_lines.append(f"        {key}={repr(val)},")
                    elif key == "strategy" and val == "list":
                        continue # Skip default strategy
                    else:
                        new_code_lines.append(f"        {key}={repr(val)},")
                else:
                    new_code_lines.append(f"        {key}={val},")
        
        new_code_lines.append("    ),")
    new_code_lines.append("]")
    
    # Locate FIELDS assignment in original file
    source = "".join(lines)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
        
    start_lineno = -1
    end_lineno = -1
    
    for node in ast.walk(tree):
        is_target = False
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "FIELDS": is_target = True
        elif isinstance(node, ast.AnnAssign):
             if isinstance(node.target, ast.Name) and node.target.id == "FIELDS": is_target = True
             
        if is_target:
            start_lineno = node.lineno
            end_lineno = node.end_lineno
            break
            
    if start_lineno == -1: return False
    
    # Splice
    # AST end_lineno covers the whole list.
    
    # However, we need to be careful about preserving what was AFTER the list
    # The previous logic was robust enough.
    
    final_content = "".join(lines[:start_lineno-1]) + "\n".join(new_code_lines) + "\n" + "".join(lines[end_lineno:])
    
    # Handle VALIDATION_GROUPS preservation logic if needed (it was in the old code to be safe)
    # The simple splice above assumes there's nothing *inside* the list definition we want to keep (which is true).
    # And it assumes lines[end_lineno:] covers the rest.
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_content)
        
    return True


def write_field_registry_md(file_path: Path, fields: List[DynamicFieldSpec]) -> bool:
    """
    Update FIELD_REGISTRY.md.
    """
    import json
    
    # Load canonical ID3 frames
    id3_frames = _load_id3_frames(file_path)
    
    field_to_frame = {}
    for frame_code, info in id3_frames.items():
        if isinstance(info, dict) and "field" in info:
            field_to_frame[info["field"]] = frame_code
            
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    # Table bounds finding
    table_start = -1
    table_end = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("| Name") and "UI Header" in line:
            table_start = i
            table_end = i + 2
            continue
        if table_start != -1 and i > table_start + 1:
            if not line.strip() or line.startswith("##") or line.startswith("**Total:"):
                table_end = i
                break
            table_end = i + 1
            
    if table_start == -1: return False
    
    new_rows = []
    for f in fields:
        yes_no = lambda k: "Yes" if f.get(k) is True else "No"
        id3 = field_to_frame.get(f.name, "—")
        
        strat = f.get("strategy", "list")
        strategy_display = {
            "range": "Range Filter",
            "boolean": "Boolean Toggle",
            "decade_grouper": "Decade Grouping",
            "first_letter_grouper": "First Letter",
        }.get(strat, "")
        
        row = f"| `{f.name}` | {f.ui_header} | {f.db_column} | {f.get('field_type', 'TEXT')} | {strategy_display} | {yes_no('visible')} | {yes_no('editable')} | {yes_no('filterable')} | {yes_no('searchable')} | {yes_no('required')} | {yes_no('portable')} | {id3} |"
        new_rows.append(row + "\n")
        
    final_lines = lines[:table_start+2] + new_rows + lines[table_end:]
    
    # Update Total
    for i in range(len(final_lines)):
        if final_lines[i].strip().startswith("**Total:"):
            final_lines[i] = f"**Total: {len(fields)} fields**\n"
            break
            
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(final_lines)
        
    return True

def _load_id3_frames(md_file_path: Path) -> Dict[str, Any]:
    """Internal helper to load ID3 frames relative to the MD file."""
    import json
    try:
        json_path = md_file_path.parent.parent / "src" / "resources" / "id3_frames.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as jf:
                return json.load(jf)
    except Exception:
        pass
    return {}
