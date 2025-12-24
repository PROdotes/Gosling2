
import json
import ast
import os
import sys

def analyze_file(filepath, executed_lines, missing_lines):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Determine class context
            parent = getattr(node, 'parent', None)
            class_name = parent.name if isinstance(parent, ast.ClassDef) else None
            
            func_name = node.name
            start_line = node.lineno
            end_line = getattr(node, 'end_lineno', start_line)
            
            # Helper to check if a line falls within this function
            # We assume a function covers lines from def to end.
            
            total_lines_in_func = set(range(start_line, end_line + 1))
            
            # Intersection with execution data
            covered = total_lines_in_func.intersection(executed_lines)
            missed = total_lines_in_func.intersection(missing_lines)
            
            # Simple heuristic: if any line is executed, it's "Covered".
            # If 0 lines executed, check if it's empty/pass/docstring ONLY.
            
            is_covered = len(covered) > 0
            
            coverage_pct = 0
            if (len(covered) + len(missed)) > 0:
                coverage_pct = int((len(covered) / (len(covered) + len(missed))) * 100)
                
            full_name = f"{class_name}.{func_name}" if class_name else func_name
            
            results.append({
                'name': full_name,
                'file': filepath,
                'coverage': coverage_pct,
                'covered_lines': len(covered),
                'missed_lines': len(missed),
                'start_line': start_line
            })
            
    # Hack to link parents for ClassName detection (ast.walk doesn't do this by default)
    # Rerunning with parent tagging
    return results

def tag_parents(node):
    for child in ast.iter_child_nodes(node):
        child.parent = node
        tag_parents(child)

def main():
    if not os.path.exists('coverage.json'):
        print("coverage.json not found!")
        return

    with open('coverage.json') as f:
        data = json.load(f)

    report_lines = []
    report_lines.append("# 🧪 Test Coverage Gap Analysis")
    report_lines.append("This inventory maps every function in `src/` to its code coverage status.")
    report_lines.append("")
    report_lines.append("| File | Function | Coverage | Status |")
    report_lines.append("| :--- | :--- | :--- | :--- |")

    # Group by file
    files = sorted(data['files'].keys())
    
    for relative_path in files:
        # relative_path is usually like src/core/yellberus.py
        # Skip weird stuff
        if not relative_path.startswith('src'):
            continue
            
        executed = set(data['files'][relative_path]['executed_lines'])
        missing = set(data['files'][relative_path]['missing_lines'])
        
        abs_path = os.path.abspath(relative_path)
        
        # Read file and finding functions
        try:
           with open(abs_path, 'r', encoding='utf-8') as f:
               tree = ast.parse(f.read())
               tag_parents(tree)
               
               for node in ast.walk(tree):
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Get Class Name if any
                        class_name = ""
                        curr = node
                        while hasattr(curr, 'parent'):
                            curr = curr.parent
                            if isinstance(curr, ast.ClassDef):
                                class_name = curr.name
                                break
                        
                        full_name = f"{class_name}.{node.name}" if class_name else node.name
                        
                        # Calculate Coverage
                        # Lines relevant to this function
                        func_lines = set(range(node.lineno, node.end_lineno + 1))
                        
                        # Intersection
                        f_exec = func_lines.intersection(executed)
                        f_miss = func_lines.intersection(missing)
                        
                        total_relevant = len(f_exec) + len(f_miss)
                        
                        if total_relevant == 0:
                            continue # Abstract method or docstring only
                            
                        pct = int((len(f_exec) / total_relevant) * 100)
                        
                        status = "✅"
                        if pct < 50: status = "🔴"
                        elif pct < 90: status = "⚠️"
                        
                        # Only report significant functions (skip __str__, __repr__ if covered)
                        if node.name.startswith("__") and pct == 100:
                            continue
                            
                        report_lines.append(f"| `{relative_path}` | `{full_name}` | {pct}% | {status} |")
                        
        except Exception as e:
            print(f"Failed to parse {relative_path}: {e}")
            
    with open('design/specs/TEST_COVERAGE_GAP_ANALYSIS.md', 'w', encoding='utf-8') as out:
        out.write("\n".join(report_lines))
        
    print("Report generated at design/specs/TEST_COVERAGE_GAP_ANALYSIS.md")

if __name__ == "__main__":
    main()
