import sqlite3
import os

db_path = os.path.join("sqldb", "gosling2.sqlite3")

def seed():
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("Seeding Dave Grohl (The Man, The Myth, The Legend)...")

    try:
        # 1. Get IDs for Nirvana and Foo Fighters
        bands = {}
        for band in ["Nirvana", "Foo Fighters"]:
            cursor.execute("SELECT ContributorID FROM Contributors WHERE ContributorName = ?", (band,))
            row = cursor.fetchone()
            if row:
                bands[band] = row[0]
                # Update Type to 'group' just in case
                cursor.execute("UPDATE Contributors SET Type = 'group' WHERE ContributorID = ?", (row[0],))
            else:
                print(f"Warning: {band} not found! Did the app run?")
                return

        # 2. Create Dave Grohl
        cursor.execute("INSERT OR IGNORE INTO Contributors (ContributorName, Type) VALUES (?, ?)", ("Dave Grohl", "person"))
        cursor.execute("SELECT ContributorID FROM Contributors WHERE ContributorName = ?", ("Dave Grohl",))
        dave_id = cursor.fetchone()[0]
        print(f"Dave Grohl ID: {dave_id}")

        # 3. Link Dave to Bands
        for band, band_id in bands.items():
            print(f"Linking Dave into {band} (ID: {band_id})...")
            cursor.execute("INSERT OR IGNORE INTO GroupMembers (GroupID, MemberID) VALUES (?, ?)", (band_id, dave_id))

        # 4. Create Alias "Dale Nixon"
        print("Creating Alias 'Dale Nixon'...")
        cursor.execute("INSERT OR IGNORE INTO ContributorAliases (ContributorID, AliasName) VALUES (?, ?)", (dave_id, "Dale Nixon"))
        
        conn.commit()
        print("Seeding Complete. Rock on.")

    except Exception as e:
        print(f"Seeding Failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    seed()
