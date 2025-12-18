"""
Audit DATABASE.md for consistency between:
1. Mermaid diagram entity definitions
2. Text table definitions (markdown tables)

This script parses both sections and reports discrepancies.
"""
import re

md_path = 'DATABASE.md'

with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# 1. Parse Mermaid Diagram (Target Architecture)
# ============================================================
mermaid_pattern = re.compile(r'### 2\. Target Architecture Schema.*?```mermaid(.*?)```', re.DOTALL)
mermaid_match = mermaid_pattern.search(content)

mermaid_entities = {}
if mermaid_match:
    mermaid_block = mermaid_match.group(1)
    # Parse entity blocks: TableName { ... } or TableName["Label"] { ... }
    entity_pattern = re.compile(r'^\s{4}(\w+)(?:\[.*?\])?\s*\{(.*?)\}', re.MULTILINE | re.DOTALL)
    for match in entity_pattern.finditer(mermaid_block):
        table_name = match.group(1)
        body = match.group(2)
        fields = []
        for line in body.split('\n'):
            line = line.strip()
            if not line: continue
            parts = line.split()
            if len(parts) >= 2:
                # Format: TYPE FieldName [PK/FK]
                field_name = parts[1]
                fields.append(field_name)
        mermaid_entities[table_name] = set(fields)

# ============================================================
# 2. Parse Markdown Table Definitions
# ============================================================
text_entities = {}

# Find headings like "### 1. `Types`" or "### `Timeslots`"
# Then find the table below and extract column names

# Split content by table headings
heading_pattern = re.compile(r'^### (?:\d+\.\s*)?`?(\w+)`?.*?$', re.MULTILINE)
sections = heading_pattern.split(content)

# sections alternates: [text_before, table_name, text_after_table, table_name2, ...]
i = 1
while i < len(sections):
    table_name = sections[i]
    if i + 1 < len(sections):
        section_text = sections[i + 1]
    else:
        section_text = ""
    
    # Skip non-table sections
    if table_name in ['Overview', 'Completeness', 'Schema', 'Core', 'Business', 
                       'Tags', 'Playlists', 'Audit', 'Contributors', 'Albums', 
                       'Summary', 'Future', 'Repositories', 'Migration']:
        i += 2
        continue
    
    # Find markdown table in section
    table_pattern = re.compile(r'\| Column \| Type \|.*?\n\|[-\s|]+\n((?:\|.*?\n)+)', re.DOTALL)
    table_match = table_pattern.search(section_text)
    
    if table_match:
        rows = table_match.group(1).strip().split('\n')
        fields = []
        for row in rows:
            cols = [c.strip() for c in row.split('|')]
            if len(cols) > 2:
                col_name = cols[1].replace('`', '').strip()
                if col_name:
                    fields.append(col_name)
        if fields:
            text_entities[table_name] = set(fields)
    
    i += 2

# ============================================================
# 3. Compare and Report
# ============================================================
report_lines = []
report_lines.append("=" * 80)
report_lines.append("DATABASE.MD VALIDATION REPORT")
report_lines.append("=" * 80)
report_lines.append("")

# All known entities
all_entities = sorted(set(mermaid_entities.keys()) | set(text_entities.keys()))

report_lines.append(f"{'Entity':<35} | {'Text Fields':<12} | {'Diagram Fields':<14} | Status")
report_lines.append("-" * 80)

issues = []
ok_count = 0

for entity in all_entities:
    text_fields = text_entities.get(entity, set())
    mermaid_fields = mermaid_entities.get(entity, set())
    
    if text_fields == mermaid_fields and text_fields:
        status = "✅ OK"
        ok_count += 1
    elif not text_fields and mermaid_fields:
        # Only in diagram
        status = "⚠️ Only in Diagram"
        issues.append((entity, "Only in Diagram", mermaid_fields, set()))
    elif text_fields and not mermaid_fields:
        # Only in text
        status = "❌ Missing from Diagram"
        issues.append((entity, "Missing from Diagram", set(), text_fields))
    else:
        # Both exist but differ
        missing_in_mermaid = text_fields - mermaid_fields
        missing_in_text = mermaid_fields - text_fields
        if missing_in_mermaid:
            status = f"⚠️ Diagram missing {len(missing_in_mermaid)} fields"
            issues.append((entity, "Diagram missing fields", missing_in_mermaid, set()))
        elif missing_in_text:
            status = f"⚠️ Text missing {len(missing_in_text)} fields"
            issues.append((entity, "Text missing fields", set(), missing_in_text))
        else:
            status = "✅ OK"
            ok_count += 1
    
    report_lines.append(f"{entity:<35} | {len(text_fields):<12} | {len(mermaid_fields):<14} | {status}")

report_lines.append("-" * 80)
report_lines.append("")
report_lines.append(f"SUMMARY: {ok_count}/{len(all_entities)} entities match")
report_lines.append(f"         Text definitions: {len(text_entities)} entities")
report_lines.append(f"         Diagram definitions: {len(mermaid_entities)} entities")
report_lines.append("")

if issues:
    report_lines.append("ISSUES TO REVIEW:")
    report_lines.append("-" * 40)
    for entity, issue_type, set1, set2 in issues:
        report_lines.append(f"  {entity}: {issue_type}")
        if set1:
            report_lines.append(f"    -> {set1}")
        if set2:
            report_lines.append(f"    -> {set2}")
else:
    report_lines.append("✅ ALL ENTITIES MATCH - NO ISSUES FOUND")

report_lines.append("")
report_lines.append("=" * 80)

# Write report
with open('validation_report.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))

print('\n'.join(report_lines))
