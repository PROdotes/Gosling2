import os
import re
from collections import defaultdict

# Pattern for ### method_name(args) -> return_type
lookup_pattern = re.compile(r"^### ([a-zA-Z0-9_]+)\(")
duplicates = defaultdict(list)

lookup_dir = "docs/lookup"
for file in os.listdir(lookup_dir):
    if file.endswith(".md"):
        path = os.path.join(lookup_dir, file)
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                match = lookup_pattern.match(line)
                if match:
                    method_name = match.group(1)
                    duplicates[method_name].append(f"{file}:{i}")

print("Duplicate Lookup Entries:")
for name, locations in duplicates.items():
    if len(locations) > 1:
        print(f"{name}: {', '.join(locations)}")
