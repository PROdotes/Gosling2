import os
import re
from collections import defaultdict

method_pattern = re.compile(r"^\s+def ([a-zA-Z0-9_]+)\(")
duplicates = defaultdict(list)

for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    match = method_pattern.match(line)
                    if match:
                        method_name = match.group(1)
                        if method_name not in [
                            "__init__",
                            "_get_connection",
                            "get_connection",
                        ]:
                            duplicates[method_name].append(f"{path}:{i}")

for name, locations in duplicates.items():
    if len(locations) > 1:
        print(f"{name}: {', '.join(locations)}")
