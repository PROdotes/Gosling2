import sqlite3
import os

db_path = 'sqldb/gosling2.sqlite3'

try:
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"Connected to database: {db_path}")

    # Search for "Wheels"
    query = """
    SELECT 
        s.SourceID,
        ms.Name,
        ms.IsActive,
        s.IsDone,
        s.IsDone
    FROM Songs s
    JOIN MediaSources ms ON s.SourceID = ms.SourceID
    WHERE ms.Name LIKE '%wheels%'
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()

    if not rows:
        print("No song found with 'Wheels' in the name.")
    else:
        for row in rows:
            print(f"--- Song: {row['Name']} ---")
            print(f"SourceID: {row['SourceID']}")
            print(f"IsActive: {row['IsActive']} (Type: {type(row['IsActive'])})")
            print(f"IsDone: {row['IsDone']} (Type: {type(row['IsDone'])})")
            print(f"IsDone: {row['IsDone']} (Type: {type(row['IsDone'])})")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
