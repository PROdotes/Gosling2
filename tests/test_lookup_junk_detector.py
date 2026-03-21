import os
import ast
import glob
import pytest


def get_all_documented_signatures(lookup_dir: str):
    """
    Parses lookup MDs into a list of documented signatures with their locations.
    Returns: List of (md_file, line_num, name, py_file_path)
    """
    documented = []
    # Force absolute lookup_dir
    lookup_dir = os.path.abspath(lookup_dir)
    
    for md_file in glob.glob(os.path.join(lookup_dir, "*.md")):
        if md_file.endswith("instructions.md"):
            continue
        with open(md_file, "r", encoding="utf-8") as f:

            lines = f.readlines()

        top_location = None
        # Find global location at the top of the file
        for line in lines:
            if line.startswith("## "):  # Stop before sections
                break
            if "*Location:" in line:
                try:
                    top_location = line.split("`")[1].strip()
                except IndexError:
                    pass

        current_location = top_location
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Update location if specific to section
            if "*Location:" in line:
                try:
                    current_location = line.split("`")[1].strip()
                except IndexError:
                    pass

            # Detect Class Header (## ClassName)
            if line.startswith("## "):
                # Extract first word after ## (header name)
                parts = line[3:].strip().split()
                if parts:
                    name = parts[0]
                    if name and current_location:
                        documented.append((md_file, line_num, name, current_location))

            # Detect Method/Function (### signature)
            if line.startswith("### "):
                # e.g. "### get_by_id(id: int)" -> "get_by_id"
                # e.g. "### app: FastAPI" -> "app"
                sig_part = line[4:].strip().split("(")[0].strip()
                if sig_part:
                    # Remove type hints if it's a variable (e.g. app: FastAPI)
                    name_part = sig_part.split(":")[0].strip()
                    # Handle "async def name" or "def name" or just "name"
                    name = name_part.split()[-1]
                    if name and current_location:
                        documented.append((md_file, line_num, name, current_location))

    
    return documented


def get_actual_members(path: str):
    """Find all classes, methods, functions, and global variables in a file/directory."""
    if not os.path.isabs(path):
        path = os.path.abspath(path)
        
    if not os.path.exists(path):
        return None
    
    if os.path.isdir(path):
        all_members = set()
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    file_members = get_actual_members(os.path.join(root, file))
                    if file_members:
                        all_members.update(file_members)
        return all_members

    try:
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except Exception:
        return set()

    members = set()
    for node in tree.body:
        # Functions and Classes
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            members.add(node.name)
            # Methods within classes
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        members.add(item.name)
        # Global assignments (e.g., app = FastAPI())
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    members.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                members.add(node.target.id)
                
    return members


def test_lookup_junk_detection():
    """
    JUNK DETECTION: Every signature documented in docs/lookup/
    must actually exist in the source code.
    """
    lookup_dir = os.path.abspath("docs/lookup")
    
    if not os.path.exists(lookup_dir):
        pytest.fail(f"Lookup directory missing: {lookup_dir}")

    documented = get_all_documented_signatures(lookup_dir)
    errors = []
    
    actual_cache = {}

    for md_file, line_num, name, py_file_path in documented:
        abs_py_path = os.path.abspath(py_file_path)
        
        if abs_py_path not in actual_cache:
            actual = get_actual_members(abs_py_path)
            actual_cache[abs_py_path] = actual

        actual = actual_cache[abs_py_path]
        
        rel_md = os.path.relpath(md_file, os.path.abspath("."))
        
        if actual is None:
            errors.append(
                f"[FILE MISSING] {rel_md}:{line_num} references non-existent path: `{py_file_path}`"
            )
            continue

        with open(md_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            header_line = lines[line_num - 1]
            is_signature = header_line.startswith("###")

        if is_signature:
            # Extract raw signature part for filtering
            sig_part = header_line[4:].strip().split("(")[0].strip()
            
            # Skip common meta-headers or intentional documentation elements
            if name in ("Location:", "Layer", "Protocol", "Responsibility", "Status:", "Contract:", "HTTP:"):
                continue
            # Skip things that look like routes, filesystem paths, or JS-style filenames
            if "/" in sig_part or "*" in sig_part or sig_part.endswith(".js"):
                continue
            
            # Junk Detection Law: Member verification only for Python files.
            # If the documented location is not a Python file/dir, we skip member verification.
            if not py_file_path.endswith(".py") and not os.path.isdir(abs_py_path):
                continue

            if name not in actual:
                errors.append(
                    f"[GHOST SIGNATURE] '{name}' documented in {rel_md}:{line_num} not found in `{py_file_path}`"
                )




    if errors:
        summary = "\n".join(errors)
        pytest.fail(f"Lookup Junk Protocol Violation:\n{summary}")

