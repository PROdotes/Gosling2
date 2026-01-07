"""
Canary test to ensure all CRUD operations have proper audit logging.

This test scans the codebase for INSERT/UPDATE/DELETE SQL statements
and verifies that the containing method also has AuditLogger calls with batch_id.
"""
import ast
import os
import re
from pathlib import Path
import pytest


# Patterns to detect CRUD operations
CRUD_PATTERNS = [
    r'INSERT\s+INTO',
    r'INSERT\s+OR\s+IGNORE\s+INTO', 
    r'UPDATE\s+\w+\s+SET',
    r'DELETE\s+FROM',
]

# Tables that are ALLOWED to be unaudited (audit tables themselves, read-only, etc.)
ALLOWED_UNAUDITED_TABLES = {
    'ChangeLog',      # The audit table itself
    'DeletedRecords', # The audit table itself
    'ActionLog',      # The audit table itself
    'Roles',          # Static lookup table, rarely changes
}

# Methods that are ALLOWED to skip auditing (called by audited higher-level methods)
ALLOWED_UNAUDITED_METHODS = {
    '_insert_db',     # Called by GenericRepository.insert which audits
    '_update_db',     # Called by GenericRepository.update which audits
    '_delete_db',     # Called by GenericRepository.delete which audits
}


def get_source_files():
    """Get all Python files in src/ directory (excluding presentation layer and schema init)."""
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


def extract_methods_with_crud(source_code: str, file_path: str):
    """
    Parse Python source and find methods containing CRUD SQL.
    Returns list of (method_name, line_number, crud_type, table_name, has_audit, has_batch_id)
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
            
            # Skip allowed methods
            if method_name in ALLOWED_UNAUDITED_METHODS:
                continue
            
            # Check for CRUD patterns
            for pattern in CRUD_PATTERNS:
                matches = re.finditer(pattern, method_source, re.IGNORECASE)
                for match in matches:
                    # Try to extract table name
                    table_match = re.search(
                        pattern + r'\s+(\w+)', 
                        method_source[match.start():match.start()+100], 
                        re.IGNORECASE
                    )
                    table_name = table_match.group(1) if table_match else 'UNKNOWN'
                    
                    # Skip allowed unaudited tables
                    if table_name in ALLOWED_UNAUDITED_TABLES:
                        continue
                    
                    # Check if AuditLogger is present in method
                    has_audit = 'AuditLogger' in method_source or 'auditor' in method_source.lower()
                    
                    # Check if batch_id is passed - either:
                    # 1. batch_id= explicitly passed to AuditLogger
                    # 2. Method accepts 'auditor' param (caller provides it with batch_id)
                    # 3. batch_id is a method parameter
                    has_batch_id = (
                        'batch_id=' in method_source or 
                        'batch_id)' in method_source or
                        'auditor: ' in method_source or  # Method accepts auditor param
                        'auditor=' in method_source or   # Optional auditor param
                        ', auditor)' in method_source    # Auditor passed to call
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
            errors.append(f"  - {f['file']}:{f['line']} {f['method']}() -> {f['crud_type']} {f['table']}")
    
    if missing_batch_id:
        errors.append("\n⚠️ Audit calls WITHOUT batch_id:\n")
        for f in missing_batch_id:
            errors.append(f"  - {f['file']}:{f['line']} {f['method']}() -> {f['crud_type']} {f['table']}")
    
    if errors:
        pytest.fail('\n'.join(errors))


def test_no_audit_logger_without_batch_id():
    """
    Stricter test: Find any AuditLogger(conn) call that doesn't pass batch_id.
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
