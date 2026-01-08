import sqlite3
import os

db_path = os.path.join("sqldb", "gosling2.db")

def inspect():
    if not os.path.exists(db_path):
        print(f"❌ DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Inspecting Songs ('Lithium', 'Pretender')...")
    
    query = """
    SELECT 
        MS.SourceID, 
        MS.Name, 
        S.Groups, 
        C.ContributorName, 
        R.RoleName
    FROM MediaSources MS
    LEFT JOIN Songs S ON MS.SourceID = S.SourceID
    LEFT JOIN MediaSourceContributorRoles MSCR ON MS.SourceID = MSCR.SourceID
    LEFT JOIN Contributors C ON MSCR.ContributorID = C.ContributorID
    LEFT JOIN Roles R ON MSCR.RoleID = R.RoleID
    WHERE MS.Name LIKE '%Lithium%' OR MS.Name LIKE '%Pretender%'
    ORDER BY MS.Name
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print("No songs found.")
        return

    current_song = None
    for row in rows:
        sid, name, groups, contributor, role = row
        if name != current_song:
            print(f"\nSong: {name} (ID: {sid})")
            print(f"   S.Groups (Zombie): '{groups}'")
            current_song = name
        
        if contributor:
            print(f"   Contributor: {contributor} ({role})")
        else:
            print(f"   No Contributors linked.")

    print("\n--- 3. Contributors Dump ---")
    cursor.execute("SELECT ContributorID, ContributorName, Type FROM Contributors")
    for row in cursor.fetchall():
        print(f"ID: {row[0]} | Name: {row[1]} | Type: {row[2]}")

    conn.close()

if __name__ == "__main__":
    inspect()
