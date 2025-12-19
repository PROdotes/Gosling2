
import pyodbc
import sys
import os

# Configuration - Update this path to point to your actual test DB
DB_PATH = r"\\Onair\Jazler RadioStar 2\Databases - Copy\Songs.mdb" # Try the path you mentioned
# If that failes, fallback to local test if available
# DB_PATH = r"C:\path\to\local\copy.mdb" 

def check_encoding():
    print(f"--- Checking Database Encoding ---")
    print(f"Target DB: {DB_PATH}")
    
    conn_str = f'Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={DB_PATH};'
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("✅ Connection Successful!")
        
        # We need to find a table and column to query. 
        # Based on SongController.java, the table is likely 'Songs' or similar.
        # I'll try to list tables first to be safe.
        print("\n--- Listing Tables ---")
        tables = [row.table_name for row in cursor.tables()]
        print(f"Found tables: {tables}")
        
        target_table = "Songs" if "Songs" in tables else tables[0]
        print(f"\n--- Querying Table: {target_table} ---")
        
        # Try to find a row with special chars
        # We look for common Croatian chars: č, ć, đ, š, ž
        special_chars = ['č', 'ć', 'đ', 'š', 'ž', 'Č', 'Ć', 'Đ', 'Š', 'Ž']
        
        found_any = False
        
        # Select first 50 rows and inspect them in Python
        cursor.execute(f"SELECT TOP 50 * FROM {target_table}")
        columns = [column[0] for column in cursor.description]
        print(f"Columns: {columns}")
        
        for row in cursor.fetchall():
            row_data = dict(zip(columns, row))
            # Just inspect string columns
            for col, val in row_data.items():
                if isinstance(val, str):
                    for char in special_chars:
                        if char in val:
                            print(f"\n🔥 FOUND SPECIAL CHAR '{char}' in column '{col}'!")
                            print(f"    Raw Value: {val}")
                            print(f"    Repr: {ascii(val)}")
                            found_any = True
                            
            if found_any:
                break
        
        if not found_any:
            print("\n⚠️ No special characters found in the first 50 rows.")
            print("Try running a specific query like: SELECT * FROM Songs WHERE Artist LIKE '%đ%'")
            
        conn.close()
        
    except pyodbc.Error as e:
        print(f"\n❌ Database Error: {e}")
        print("Note: You might need to install 'Microsoft Access Database Engine 2010/2016' if drivers are missing.")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")

if __name__ == "__main__":
    check_encoding()
