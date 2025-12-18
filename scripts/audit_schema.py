import re

md_path = 'DATABASE.md'

with open(md_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Parse Mermaid Diagram (Target Architecture)
mermaid_pattern = re.compile(r'### 2\. Target Architecture Schema.*?```mermaid(.*?)```', re.DOTALL)
mermaid_match = mermaid_pattern.search(content)

mermaid_tables = {}
if mermaid_match:
    mermaid_block = mermaid_match.group(1)
    # Parse entity blocks: TableName { ... }
    entity_pattern = re.compile(r'(\w+)(?:\[".*?"\])?\s*\{(.*?)\}', re.DOTALL)
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
                # We care about the FieldName, which is usually the second item
                # But sometimes it might be "INTEGER FieldName PK" or "TEXT FieldName"
                # Mermaid syntax in the file seems to conform to: TYPE Name [Constraints]
                field_name = parts[1]
                fields.append(field_name)
        mermaid_tables[table_name] = set(fields)

# 2. Parse Markdown Tables
# Looking for headings like: ### 1. `Types` ... followed by a markdown table
# We need to capture the Table Name and the Column names from the table following it.
text_tables = {}

# Regex to find headings like "### 1. `Types`" or "### `Timeslots`"
heading_pattern = re.compile(r'### \d*\.?\s*`?(\w+)`?')

lines = content.split('\n')
current_table = None
in_table_header = False
table_header_line_count = 0

for i, line in enumerate(lines):
    line = line.strip()
    
    # Check for heading
    heading_match = heading_pattern.match(line)
    if heading_match:
        current_table = heading_match.group(1)
        in_table_header = False
        continue
        
    if current_table:
        # Look for table start
        if line.startswith('| Column |') or line.startswith('| Field |'):
             in_table_header = True
             table_header_line_count = 0
             continue
        
        if in_table_header:
            if line.startswith('|-'):
                continue
            if line.startswith('|'):
                # Data row
                parts = [p.strip() for p in line.split('|')]
                if len(parts) > 2:
                    col_name = parts[1].replace('`', '').strip()
                    if col_name and col_name != 'Field' and col_name != 'Column':
                        if current_table not in text_tables:
                            text_tables[current_table] = set()
                        text_tables[current_table].add(col_name)
            else:
                # End of table
                if line == '' and table_header_line_count > 0: 
                     # Only reset if we actually processed some table part, 
                     # but here simply non-pipe line ends table
                     pass 
        

# 3. Compare

with open('audit_report.txt', 'w', encoding='utf-8') as report:
    report.write(f"{'Table':<30} | {'Plan (Text)':<10} | {'Diagram':<10} | {'Status':<10}\n")
    report.write("-" * 70 + "\n")

    all_tables = sorted(list(set(text_tables.keys()) | set(mermaid_tables.keys())))

    total_text_fields = 0
    total_mermaid_fields = 0

    for table in all_tables:
        text_fields = text_tables.get(table, set())
        mermaid_fields = mermaid_tables.get(table, set())
        
        # Filter out weird matches if any
        if table in ['1', '2', 'Overview']: continue 

        # Comparison
        missing_in_mermaid = text_fields - mermaid_fields
        missing_in_text = mermaid_fields - text_fields
        
        status = "OK"
        if missing_in_mermaid: status = "Missing in Diagram"
        if missing_in_text: status = f"Missing in Text ({len(missing_in_text)})"
        
        # Strict equality check
        if text_fields != mermaid_fields:
            if not missing_in_mermaid and not missing_in_text:
                 status = "OK" # Order doesn't matter for sets
            elif missing_in_mermaid:
                 status = f"Mermaid Missing: {', '.join(list(missing_in_mermaid)[:3])}"
            else:
                 status = f"Text Missing: {', '.join(list(missing_in_text)[:3])}"

        report.write(f"{table:<30} | {len(text_fields):<10} | {len(mermaid_fields):<10} | {status}\n")
        
        if missing_in_mermaid:
            report.write(f"  -> Missing in Mermaid: {missing_in_mermaid}\n")
        if missing_in_text:
            report.write(f"  -> Missing in Text: {missing_in_text}\n")

        total_text_fields += len(text_fields)
        total_mermaid_fields += len(mermaid_fields)

    report.write("-" * 70 + "\n")
    report.write(f"{'TOTAL':<30} | {total_text_fields:<10} | {total_mermaid_fields:<10} |\n")
