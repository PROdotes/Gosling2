"""
Junk detection test for the Lookup Protocol (Rule 2).

Verifies that every signature documented in docs/lookup/*.md actually
exists in the referenced source file. Catches stale/garbage entries.
"""

import os
import ast
import glob


def get_all_documented_signatures(lookup_dir: str):
    """
    Parses lookup MDs into a list of documented signatures with their locations.
    Returns: List of (md_file, line_num, name, py_file_path)
    """
    documented = []
    lookup_dir = os.path.abspath(lookup_dir)

    for md_file in glob.glob(os.path.join(lookup_dir, "*.md")):
        if md_file.endswith("instructions.md"):
            continue
        with open(md_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        top_location = None
        for line in lines:
            if line.startswith("## "):
                break
            if "*Location:" in line:
                try:
                    top_location = line.split("`")[1].strip()
                except IndexError:
                    pass

        current_location = top_location
        for i, line in enumerate(lines):
            line_num = i + 1

            if "*Location:" in line:
                try:
                    current_location = line.split("`")[1].strip()
                except IndexError:
                    pass

            if line.startswith("## "):
                parts = line[3:].strip().split()
                if parts:
                    name = parts[0]
                    if name and current_location:
                        documented.append((md_file, line_num, name, current_location))

            if line.startswith("### "):
                sig_part = line[4:].strip().split("(")[0].strip()
                if sig_part:
                    name_part = sig_part.split(":")[0].strip()
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
                if file.endswith((".py", ".js")):
                    file_members = get_actual_members(os.path.join(root, file))
                    if file_members:
                        all_members.update(file_members)
        return all_members

    if path.endswith(".py"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            members = set()
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    members.add(node.name)
                    if isinstance(node, ast.ClassDef):
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                members.add(item.name)
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if hasattr(node, "targets") else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Name):
                            members.add(target.id)
            return members
        except Exception:
            return set()

    if path.endswith(".js"):
        import re
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            members = set()
            # 1. Functions, Classes, and Constants
            matches = re.finditer(r'export\s+(?:async\s+)?(?:function|class|const)\s+([a-zA-Z0-9_]+)', content)
            for m in matches:
                members.add(m.group(1))
            
            # 2. Methods in classes
            class_blocks = re.finditer(r'export\s+class\s+([a-zA-Z0-9_]+)\s*\{([\s\S]*?)\n\}', content)
            for cb in class_blocks:
                class_content = cb.group(2)
                keywords = {'if', 'for', 'while', 'catch', 'switch'}
                method_matches = re.finditer(r'^\s*(?:async\s+)?([a-zA-Z0-9][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{', class_content, re.MULTILINE)
                for mm in method_matches:
                    m_name = mm.group(1)
                    if m_name != "constructor" and m_name not in keywords:
                        members.add(m_name)
            
            # 3. Named exports
            named_matches = re.finditer(r'export\s+\{(.*)\}', content)
            for m in named_matches:
                for n in m.group(1).split(","):
                    members.add(n.strip())
            
            # 4. Local functions (for shared.js/utils.js where they aren't always exported)
            local_matches = re.finditer(r'(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(', content)
            for m in local_matches:
                members.add(m.group(1))
                
            return members
        except Exception:
            return set()

    return set()


class TestLookupJunkDetector:
    def test_lookup_junk_detection(self):
        """
        JUNK DETECTION: Every signature documented in docs/lookup/
        must actually exist in the referenced source file or directory.
        """
        lookup_dir = os.path.abspath("docs/lookup")

        assert os.path.exists(lookup_dir), f"Lookup directory missing: {lookup_dir}"

        documented = get_all_documented_signatures(lookup_dir)
        file_missing_errors = []
        ghost_errors = []
        actual_cache = {}

        for md_file, line_num, name, py_file_path in documented:
            abs_py_path = os.path.abspath(py_file_path)

            if abs_py_path not in actual_cache:
                actual = get_actual_members(abs_py_path)
                actual_cache[abs_py_path] = actual

            actual = actual_cache[abs_py_path]
            rel_md = os.path.relpath(md_file, os.path.abspath("."))

            if actual is None:
                file_missing_errors.append(
                    f"[FILE MISSING] {rel_md}:{line_num} references non-existent path: `{py_file_path}`"
                )
                continue

            with open(md_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                header_line = lines[line_num - 1]
                is_signature = header_line.startswith("###")

            if is_signature:
                sig_part = header_line[4:].strip().split("(")[0].strip()

                if name in (
                    "Location:",
                    "Layer",
                    "Protocol",
                    "Responsibility",
                    "Status:",
                    "Contract:",
                    "HTTP:",
                ):
                    continue
                if "/" in sig_part or "*" in sig_part or sig_part.endswith(".js"):
                    continue

                if not py_file_path.endswith(".py") and not os.path.isdir(abs_py_path):
                    continue

                # Strip Markdown backslash escapes (e.g. \_method_name)
                clean_name = name.replace("\\", "")
                if clean_name not in actual:
                    ghost_errors.append(
                        f"[GHOST SIGNATURE] '{name}' documented in {rel_md}:{line_num} not found in `{py_file_path}`"
                    )

        assert (
            len(file_missing_errors) == 0
        ), "Junk Detector -- Missing Files:\n" + "\n".join(file_missing_errors)
        assert (
            len(ghost_errors) == 0
        ), "Junk Detector -- Ghost Signatures:\n" + "\n".join(ghost_errors)
