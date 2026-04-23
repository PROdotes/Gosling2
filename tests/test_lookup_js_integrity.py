"""
Constitutional integrity test for the JS Lookup Protocol (Rule 2).

Verifies that every public export in src/static/js/dashboard/ and its subdirectories
are documented with strict signatures in docs/lookup/js_*.md.
"""

import os
import re
import glob

def get_signatures_from_block(block_content: str):
    """Extract method/function names from ### headers in a markdown block."""
    signatures = []
    for line in block_content.split("\n"):
        line = line.strip()
        if line.startswith("### "):
            line_content = line[4:].strip()
            # Extract the name before the parenthesis
            sig_part = line_content.split("(")[0].strip()
            if sig_part:
                # Get the last word (e.g. 'function_name' from 'async function function_name')
                name = sig_part.split()[-1]
                signatures.append(name)
    return signatures

def get_documented_map(lookup_dir: str):
    """
    Parses lookup MDs into a map of absolute_path -> set of documented names.
    Supports top-level Location and per-section/per-signature overrides.
    """
    doc_map = {}
    md_files = glob.glob(os.path.join(lookup_dir, "js_*.md")) + [os.path.join(lookup_dir, "dashboard_ui.md")]
    
    for md_file in md_files:
        if not os.path.exists(md_file):
            continue
            
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read().replace("\r", "")

        top_location = None
        # Parse top-level location
        main_header_block = re.split(r'\n##\s+|\n###\s+', content)[0]
        for line in main_header_block.split("\n"):
            line = line.strip()
            if line.startswith("*Location:"):
                try:
                    top_location = line.split("`")[1].strip()
                    break
                except IndexError:
                    pass

        # Split into units (starting with ## or ###)
        # Using lookahead to keep the separator
        units = re.split(r'\n(?=#{2,3}\s+)', content)
        
        current_location = top_location
        for unit in units:
            # Check for location override in this unit
            for line in unit.split("\n"):
                line = line.strip()
                if line.startswith("*Location:"):
                    try:
                        current_location = line.split("`")[1].strip()
                        break
                    except IndexError:
                        pass
            
            if current_location:
                abs_loc = os.path.abspath(current_location)
                if abs_loc not in doc_map:
                    doc_map[abs_loc] = set()
                
                signatures = get_signatures_from_block(unit)
                for sig in signatures:
                    doc_map[abs_loc].add(sig)
                
                # Also treat the header as a signature if it's not a top-level # header
                # (for classes or named groups)
                header_match = re.match(r'^#{2,3}\s+(.*)', unit)
                if header_match:
                    header_line = header_match.group(1).strip()
                    if "(" in header_line:
                        name = header_line.split("(")[0].strip().split()[-1]
                    else:
                        name = header_line.split()[-1]
                    doc_map[abs_loc].add(name)

    return doc_map

def get_all_js_files(src_dir: str):
    """Recurse src/static/js/dashboard/ but exclude third-party or minified if any."""
    js_files = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".js") and not file.endswith(".min.js"):
                js_files.append(os.path.join(root, file))
    return js_files

def get_exports_to_verify(file_path: str):
    """Find all public exports that should be documented."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    exports = []
    # Match 'export function name(...)', 'export async function name(...)', 
    # 'export class Name', 'export const Name', 'export { name }'
    
    # 1. Top-level Functions, Classes, and Constants
    matches = re.finditer(r'export\s+(?:async\s+)?(?:function|class|const)\s+([a-zA-Z0-9_]+)', content)
    for m in matches:
        exports.append(m.group(1))
        
    # 2. Methods within exported classes (simple heuristic)
    class_blocks = re.finditer(r'export\s+class\s+([a-zA-Z0-9_]+)\s*\{([\s\S]*?)\n\}', content)
    for cb in class_blocks:
        class_content = cb.group(2)
        # Match "method(args) {" at start of line (indented)
        # Exclude common keywords that look like function calls
        keywords = {'if', 'for', 'while', 'catch', 'switch'}
        method_matches = re.finditer(r'^\s*(?:async\s+)?([a-zA-Z0-9][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{', class_content, re.MULTILINE)
        for mm in method_matches:
            method_name = mm.group(1)
            if method_name != "constructor" and method_name not in keywords:
                exports.append(method_name)

    # 3. Named exports: export { name1, name2 }
    named_matches = re.finditer(r'export\s+\{(.*)\}', content)
    for m in named_matches:
        names = m.group(1).split(",")
        for n in names:
            n = n.strip().split(" as ")[0].strip() # Handle 'name as alias'
            if n:
                exports.append(n)
                
    return list(set(exports))

class TestJsLookupIntegrity:
    def test_js_lookup_protocol_integrity(self):
        """
        CONSTITUTION CHECK: Every dashboard JS file and its exports
        must exist in docs/lookup/js_*.md with strict signatures.
        """
        src_dir = os.path.abspath("src/static/js/dashboard")
        lookup_dir = os.path.abspath("docs/lookup")

        assert os.path.exists(lookup_dir), f"Lookup directory missing: {lookup_dir}"

        doc_map = get_documented_map(lookup_dir)
        js_files = get_all_js_files(src_dir)

        assert len(js_files) > 0, f"No JS files found in '{src_dir}'"
        
        location_errors = []
        signature_errors = []

        for js_file in js_files:
            abs_path = os.path.abspath(js_file)
            abs_path_norm = abs_path.lower().replace("\\", "/")
            rel_path = os.path.relpath(js_file, os.path.abspath("."))

            covered_signatures = set()
            is_covered = False

            for loc_path, sigs in doc_map.items():
                loc_path_norm = loc_path.lower().replace("\\", "/")
                if abs_path_norm == loc_path_norm or (
                    os.path.isdir(loc_path) and abs_path_norm.startswith(loc_path_norm.rstrip("/") + "/")
                ):
                    is_covered = True
                    covered_signatures.update(sigs)
            
            if not is_covered:
                location_errors.append(
                    f"[LOCATION MISSING] {rel_path} is not mapped in any docs/lookup/js_*.md"
                )
                continue

            actual_exports = get_exports_to_verify(js_file)
            for export in actual_exports:
                # Filter out obvious non-contracts like constants if desired
                if export in ["ABORTED"]:
                    continue

                if export not in covered_signatures:
                    signature_errors.append(
                        f"[SIGNATURE MISSING] '{export}' in {rel_path} is not in docs/lookup/"
                    )

        assert (
            len(location_errors) == 0
        ), "JS Lookup Protocol -- Location Violations:\n" + "\n".join(location_errors)
        assert (
            len(signature_errors) == 0
        ), "JS Lookup Protocol -- Signature Violations:\n" + "\n".join(signature_errors)
