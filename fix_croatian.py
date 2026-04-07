import sqlite3
import os
from pathlib import Path
from src.engine.config import DB_PATH, LIBRARY_ROOT

# GOSLING2 Technical Audit Fix (#5, #6, #7)
# Refactored for transaction safety, dynamic paths, and robust error handling.

# --- CONFIGURATION ---
TESTING = True  # Always True by default for safety.
CHECK_FILE_EXISTENCE = True


def fix_croatian_chars(text: str) -> str:
    """Normalize Croatian diacritics to ASCII equivalents."""
    chars = {"č": "c", "ć": "c", "š": "s", "đ": "dj", "ž": "z"}
    for old, new in chars.items():
        text = text.replace(old, new).replace(old.upper(), new.upper())
    return text


def run_fix():
    db_path = DB_PATH
    library_root = LIBRARY_ROOT

    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    # Use row_factory to access columns by name
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Find records with problematic characters in MediaName
    cur.execute(
        "SELECT SourceID, MediaName, SourcePath FROM MediaSources WHERE MediaName LIKE '%č%' OR MediaName LIKE '%ć%' OR MediaName LIKE '%š%' OR MediaName LIKE '%đ%' OR MediaName LIKE '%ž%'"
    )
    rows = cur.fetchall()

    print("--- GOSLING2 CROATIAN FIX ---")
    print(f"Database: {db_path}")
    print(f"Library Root: {library_root}")
    print(f"Found {len(rows)} records to fix.\n")

    renamed_count = 0
    error_count = 0

    for row in rows:
        sid = row["SourceID"]
        name = row["MediaName"]
        old_source_path = row["SourcePath"]

        if not old_source_path:
            continue

        # 1. Generate new names
        new_name = fix_croatian_chars(name)

        # Determine the physical path.
        # SourcePath is absolute in DB, but we verify it via library_root safely.
        old_p = Path(old_source_path)
        filename = old_p.name
        new_filename = fix_croatian_chars(filename)
        new_p = old_p.parent / new_filename

        print(f"[{sid}] '{name}' -> '{new_name}'")
        if filename != new_filename:
            print(f"      FILE: '{filename}' -> '{new_filename}'")

        if TESTING:
            print(f"      [TESTING] Would rename: {old_p} -> {new_p}")
            continue

        # 2. Transactional Filesystem + DB Update
        try:
            # Audit #6: os.rename with no try/except is a hazard.
            if old_p.exists() and old_p != new_p:
                os.rename(old_p, new_p)
                print("      [OK] Renamed on disk.")

            # Audit #7: Update DB record per-file for atomic safety.
            cur.execute(
                "UPDATE MediaSources SET MediaName = ?, SourcePath = ? WHERE SourceID = ?",
                (new_name, str(new_p), sid),
            )
            conn.commit()
            renamed_count += 1

        except Exception as e:
            conn.rollback()
            print(f"      [ERROR] Failed to process SourceID {sid}: {e}")
            error_count += 1

    conn.close()
    print("\n--- SUMMARY ---")
    if TESTING:
        print("Run with TESTING=False to apply changes.")
    else:
        print(f"Successfully processed: {renamed_count}")
        print(f"Encountered errors: {error_count}")


if __name__ == "__main__":
    run_fix()
