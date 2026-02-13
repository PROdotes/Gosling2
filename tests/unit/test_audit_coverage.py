"""
Canary test to ensure all CRUD operations have proper audit logging.

This test scans the codebase for INSERT/UPDATE/DELETE SQL statements
and verifies that the containing method also has AuditLogger calls
with batch_id.
"""
import ast
import re
from pathlib import Path
import pytest
import io
import tokenize


# Patterns to detect CRUD operations (case-insensitive, multi-line)
CRUD_PATTERNS = [
    r'INSERT\s+INTO',
    r'INSERT\s+OR\s+IGNORE\s+INTO',
    r'INSERT\s+OR\s+REPLACE\s+INTO',
    r'REPLACE\s+INTO',
    r'UPDATE\s+\w+\s+SET',
    r'DELETE\s+FROM',
]

# Tables that are ALLOWED to be unaudited (audit tables themselves)
ALLOWED_UNAUDITED_TABLES = {
    'ChangeLog',      # The audit table itself
    'DeletedRecords', # The audit table itself
    'ActionLog',      # The audit table itself
}

# Methods that are ALLOWED to skip auditing (called by audited higher-level methods)
ALLOWED_UNAUDITED_METHODS = {
    '_insert_db',     # Called by GenericRepository.insert which audits
    '_update_db',     # Called by GenericRepository.update which audits
    '_delete_db',     # Called by GenericRepository.delete which audits
    'rename_song',    # File system operation, no database CRUD
}



def get_source_files():
    """Get all Python files in src/ directory (excluding presentation
    layer and schema init)."""
    src_dir = Path(__file__).parent.parent.parent / 'src'
    files = []
    for f in src_dir.rglob('*.py'):
        # Skip presentation layer - UI code goes through services, not direct DB access
        if 'presentation' in str(f):
            continue
        # Skip database.py - schema initialization doesn't need auditing
        if f.name == 'database.py':
            continue
        files.append(f)
    return files


def find_audit_logger_calls(tree):
    """Find all AuditLogger calls in an AST tree."""
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Direct call: AuditLogger(...)
            if isinstance(node.func, ast.Name) and node.func.id == 'AuditLogger':
                calls.append(node)
            # Attribute call: something.AuditLogger(...)
            elif isinstance(node.func, ast.Attribute) and node.func.attr == 'AuditLogger':
                calls.append(node)
    return calls

def extract_methods_with_crud(source_code: str, file_path: str):
    """
    Parse Python source and find methods containing CRUD SQL.
    Returns list of (method_name, line_number, crud_type, table_name,
    has_audit, has_batch_id)
    """
    results = []
    
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return results
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_name = node.name
            method_source = ast.get_source_segment(source_code, node)
            if not method_source:
                continue

            # Parse method AST for audit detection
            try:
                method_tree = ast.parse(method_source)
            except SyntaxError:
                continue

            # Skip allowed methods
            if method_name in ALLOWED_UNAUDITED_METHODS:
                continue

            # Check for CRUD patterns
            for pattern in CRUD_PATTERNS:
                matches = re.finditer(pattern, method_source, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    # Extract table name based on pattern type
                    if 'INSERT' in pattern.upper():
                        table_pattern = r'INSERT(?:\s+OR\s+(?:IGNORE|REPLACE))?\s+INTO\s+(\w+)'
                    elif 'REPLACE' in pattern.upper():
                        table_pattern = r'REPLACE\s+INTO\s+(\w+)'
                    elif 'UPDATE' in pattern.upper():
                        table_pattern = r'UPDATE\s+(\w+)\s+SET'
                    elif 'DELETE' in pattern.upper():
                        table_pattern = r'DELETE\s+FROM\s+(\w+)'
                    else:
                        table_name = 'UNKNOWN'
                        continue

                    table_match = re.search(
                        table_pattern,
                        method_source[match.start():match.start()+200],
                        re.IGNORECASE | re.DOTALL
                    )
                    table_name = table_match.group(1) if table_match else 'UNKNOWN'
                    
                    # Skip allowed unaudited tables
                    if table_name in ALLOWED_UNAUDITED_TABLES:
                        continue

                    # Find AuditLogger calls
                    audit_calls = find_audit_logger_calls(method_tree)
                    has_audit = len(audit_calls) > 0 or 'auditor' in method_source.lower()

                    # Check for batch_id in audit calls or method params
                    has_batch_id = False
                    if audit_calls:
                        for call in audit_calls:
                            # Check if batch_id keyword argument is present
                            if any(kw.arg == 'batch_id' for kw in call.keywords if kw):
                                has_batch_id = True
                                break
                    # Also check string patterns for indirect cases
                    if not has_batch_id:
                        has_batch_id = (
                            'batch_id=' in method_source or
                            'batch_id)' in method_source or
                            'auditor: ' in method_source or  # Method accepts auditor param
                            'auditor=' in method_source or   # Optional auditor param
                            ', auditor)' in method_source or # Auditor passed to call
                            'batch_id' in [arg.arg for arg in node.args.args if arg.arg]  # Method param
                        )
                    
                    # Determine CRUD type
                    if 'INSERT' in pattern.upper():
                        crud_type = 'INSERT'
                    elif 'UPDATE' in pattern.upper():
                        crud_type = 'UPDATE'
                    else:
                        crud_type = 'DELETE'
                    
                    results.append({
                        'file': file_path,
                        'method': method_name,
                        'line': node.lineno,
                        'crud_type': crud_type,
                        'table': table_name,
                        'has_audit': has_audit,
                        'has_batch_id': has_batch_id,
                    })
    
    return results


def test_all_crud_operations_have_audit_logging():
    """
    CANARY TEST: Ensure all CRUD operations have proper audit logging.

    This test will FAIL if any INSERT/UPDATE/DELETE operation is found
    without an accompanying AuditLogger call.
    """
    missing_audit = []
    missing_batch_id = []
    
    for file_path in get_source_files():
        # Skip test files
        if 'test' in str(file_path).lower():
            continue
        
        try:
            source_code = file_path.read_text(encoding='utf-8')
        except Exception:
            continue
        
        findings = extract_methods_with_crud(source_code, str(file_path))
        
        for finding in findings:
            if not finding['has_audit']:
                missing_audit.append(finding)
            elif not finding['has_batch_id']:
                missing_batch_id.append(finding)
    
    # Build error message
    errors = []
    
    if missing_audit:
        errors.append("\n⚠️ CRUD operations WITHOUT audit logging:\n")
        for f in missing_audit:
            errors.append(
                f"  - {f['file']}:{f['line']} {f['method']}() -> "
                f"{f['crud_type']} {f['table']}"
            )

    if missing_batch_id:
        errors.append("\n⚠️ Audit calls WITHOUT batch_id:\n")
        for f in missing_batch_id:
            errors.append(
                f"  - {f['file']}:{f['line']} {f['method']}() -> "
                f"{f['crud_type']} {f['table']}"
            )
    
    if errors:
        pytest.fail('\n'.join(errors))


def test_no_audit_logger_without_batch_id():
    """
    Stricter test: Find any AuditLogger(conn) call that doesn't pass
    batch_id.
    """
    pattern = re.compile(r'AuditLogger\(conn\)')  # Missing batch_id
    
    violations = []
    
    for file_path in get_source_files():
        # Skip test files and audit_logger itself
        if 'test' in str(file_path).lower():
            continue
        if 'audit_logger.py' in str(file_path):
            continue
        
        try:
            source_code = file_path.read_text(encoding='utf-8')
        except Exception:
            continue
        
        for i, line in enumerate(source_code.splitlines(), 1):
            if pattern.search(line):
                violations.append(f"{file_path}:{i}: {line.strip()}")
    
    if violations:
        pytest.fail(
            "Found AuditLogger(conn) calls without batch_id:\n" + 
            "\n".join(violations)
        )


def test_execute_calls_with_crud_have_audit():
    """
    Additional check: Find any direct `.execute(...)` / `.executemany(...)` calls
    that perform INSERT/UPDATE/DELETE and ensure the enclosing method/file
    also uses the auditor (AuditLogger) or accepts an `auditor` / `batch_id`.

    This catches places where SQL is composed across lines or uses
    conn.execute(...) rather than inline string patterns.
    """
    exec_pattern = re.compile(r"\.execute\s*\(|\.executemany\s*\(", re.IGNORECASE)
    crud_sql_fragment = re.compile(r"\b(INSERT|UPDATE|DELETE)\b", re.IGNORECASE)

    issues = []

    for file_path in get_source_files():
        if 'test' in str(file_path).lower():
            continue

        try:
            source_code = file_path.read_text(encoding='utf-8')
        except Exception:
            continue
        # Build AST once for the file to find enclosing functions
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            tree = None

        # Precompute function ranges -> source
        func_ranges = []
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start = getattr(node, 'lineno', None)
                    end = getattr(node, 'end_lineno', start)
                    src = ast.get_source_segment(source_code, node) or ''
                    func_ranges.append((start, end, node.name, src))

        # Scan lines for execute calls and nearby SQL fragments
        lines = source_code.splitlines()
        for i, line in enumerate(lines, 1):
            if exec_pattern.search(line):
                # Look at the argument span (this line and a few following lines)
                window = '\n'.join(lines[i-1:i+4])
                if not crud_sql_fragment.search(window):
                    continue

                # If this execute touches an ALLOWED audit table, skip
                if any(tbl in window for tbl in ALLOWED_UNAUDITED_TABLES):
                    continue

                # Find enclosing function if any
                func_name = '<module>'
                func_src = source_code
                for start, end, name, src in func_ranges:
                    if start and end and start <= i <= end:
                        func_name = name
                        func_src = src
                        break

                # Heuristic: check for AuditLogger usage or auditor/batch_id anywhere in function source
                has_audit = bool(re.search(r"AuditLogger\(|\bauditor\b|batch_id\b", func_src))

                # Skip allowed unaudited methods
                if func_name in ALLOWED_UNAUDITED_METHODS:
                    continue

                if not has_audit:
                    issues.append(f"{file_path}:{i} in {func_name}() -> execute with CRUD SQL but no auditor/batch_id in function scope")

    if issues:
        pytest.fail("Found direct execute/executemany CRUD calls without nearby audit usage:\n" + "\n".join(issues))


def test_crud_outside_repositories_has_audit_or_fails():
    """
    Ensure CRUD SQL does not live in application code outside the
    data repositories unless it has explicit audit handling nearby.

    This finds any INSERT/UPDATE/DELETE usage in Python files under
    `src/` that are NOT inside `src/data/repositories` and fails if
    the file doesn't contain AuditLogger usage or an `auditor`/`batch_id`
    parameter. This enforces the rule: repository layer owns CRUD.
    """
    src_dir = Path(__file__).parent.parent.parent / 'src'
    violations = []

    for f in src_dir.rglob('*.py'):
        # Skip presentation (UI) layer and schema init
        if 'presentation' in str(f):
            continue
        if f.name == 'database.py':
            continue

        # Skip repository files (they are allowed to have CRUD)
        if '/data/repositories/' in str(f).replace('\\', '/'):
            continue

        try:
            src = f.read_text(encoding='utf-8')
        except Exception:
            continue

        # Remove comments and string literals to avoid false positives
        try:
            tokens = tokenize.generate_tokens(io.StringIO(src).readline)
            cleaned_parts = []
            for toknum, tokval, _, _, _ in tokens:
                if toknum in (tokenize.COMMENT, tokenize.STRING):
                    continue
                cleaned_parts.append(tokval)
            cleaned_src = ''.join(cleaned_parts)
        except Exception:
            cleaned_src = src

        # If any CRUD pattern appears (after stripping strings/comments), ensure audit usage exists in the same file
        found = False
        for pattern in CRUD_PATTERNS:
            if re.search(pattern, cleaned_src, re.IGNORECASE | re.DOTALL):
                found = True
                break

        if not found:
            continue

        # Heuristic: file must reference AuditLogger or accept/forward auditor/batch_id
        if not re.search(r"AuditLogger\(|\bauditor\b|batch_id\b", src):
            violations.append(str(f))

    if violations:
        pytest.fail(
            "Found CRUD SQL in non-repository files without audit handling:\n" +
            "\n".join(violations)
        )
