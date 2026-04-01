import os
import sys


def count_lines(root="."):
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden dirs and common noise folders
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".")
            and d not in ("node_modules", "__pycache__", ".venv", "venv", "tests")
        ]
        for filename in filenames:
            if filename.endswith((".py", ".js")):
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = sum(1 for _ in f)
                    results.append((lines, filepath))
                except OSError:
                    pass
    results.sort(reverse=True)
    for lines, path in results[:10]:
        print(f"{lines:>6}  {path}")


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    count_lines(root)
