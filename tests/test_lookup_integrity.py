"""
Constitutional integrity test for the Lookup Protocol (Rule 2).

Verifies that every non-model .py file under src/ and its public classes/methods
are documented with strict signatures in docs/lookup/*.md.
"""

import os
import ast
import glob


def get_signatures_from_block(block_content: str):
    """Extract method/function names from ### headers in a markdown block."""
    signatures = []
    for line in block_content.split("\n"):
        if line.startswith("### "):
            line_content = line[4:].strip()
            sig_part = line_content.split("(")[0].strip()
            if sig_part:
                name = sig_part.split()[-1]
                signatures.append(name)
    return signatures


def get_documented_map(lookup_dir: str):
    """
    Parses lookup MDs into a map of absolute_path -> set of documented names.
    Handles both file-specific and directory-level locations.
    """
    doc_map = {}
    for md_file in glob.glob(os.path.join(lookup_dir, "*.md")):
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        top_location = None
        main_header_block = content.split("## ")[0]
        for line in main_header_block.split("\n"):
            if "*Location:" in line:
                try:
                    top_location = line.split("`")[1].strip()
                    break
                except IndexError:
                    pass

        sections = content.split("\n## ")
        for section in sections:
            if not section.strip():
                continue

            current_location = top_location
            header_line = section.split("\n")[0].strip()

            for line in section.split("\n"):
                if "*Location:" in line:
                    try:
                        current_location = line.split("`")[1].strip()
                        break
                    except IndexError:
                        pass

            if current_location:
                abs_loc = os.path.abspath(current_location)
                if abs_loc not in doc_map:
                    doc_map[abs_loc] = set()

                found_names = get_signatures_from_block(section)
                for n in found_names:
                    doc_map[abs_loc].add(n)

                if header_line and not header_line.startswith("#"):
                    name = header_line.split()[-1]
                    doc_map[abs_loc].add(name)

    return doc_map


def get_all_py_files(src_dir: str):
    """Recurse src/ but exclude models/ and __pycache__ and __init__.py."""
    py_files = []
    for root, dirs, files in os.walk(src_dir):
        if "models" in root or "__pycache__" in root:
            continue
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                py_files.append(os.path.join(root, file))
    return py_files


def get_members_to_verify(file_path: str):
    """Find all classes and methods/functions that should be documented."""
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
        except Exception:
            return []

    members = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("__"):
                members.append(node.name)
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                members.append(node.name)
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not item.name.startswith("__"):
                            members.append(item.name)
    return members


class TestLookupIntegrity:

    def test_lookup_protocol_integrity(self):
        """
        CONSTITUTION CHECK: Every non-model .py file and its methods
        must exist in docs/lookup/ with strict signatures.
        """
        src_dir = os.path.abspath("src")
        lookup_dir = os.path.abspath("docs/lookup")

        assert os.path.exists(lookup_dir), f"Lookup directory missing: {lookup_dir}"

        doc_map = get_documented_map(lookup_dir)
        py_files = get_all_py_files(src_dir)

        assert len(py_files) > 0, f"No .py files found in src_dir '{src_dir}'"
        assert (
            len(doc_map) > 0
        ), f"No documented locations found in '{lookup_dir}' -- lookup docs are empty"

        location_errors = []
        signature_errors = []

        for py_file in py_files:
            abs_path = os.path.abspath(py_file)
            rel_path = os.path.relpath(py_file, os.path.abspath("."))

            covered_signatures = set()
            is_covered = False

            for loc_path, sigs in doc_map.items():
                if abs_path == loc_path or (
                    os.path.isdir(loc_path) and abs_path.startswith(loc_path)
                ):
                    is_covered = True
                    covered_signatures.update(sigs)

            if not is_covered:
                location_errors.append(
                    f"[LOCATION MISSING] {rel_path} is not mapped in any docs/lookup/*.md"
                )
                continue

            actual_members = get_members_to_verify(py_file)
            for member in actual_members:
                if member not in covered_signatures:
                    signature_errors.append(
                        f"[SIGNATURE MISSING] '{member}' in {rel_path} is not in docs/lookup/"
                    )

        assert (
            len(location_errors) == 0
        ), "Lookup Protocol -- Location Violations:\n" + "\n".join(location_errors)
        assert (
            len(signature_errors) == 0
        ), "Lookup Protocol -- Signature Violations:\n" + "\n".join(signature_errors)
