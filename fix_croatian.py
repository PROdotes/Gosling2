import sqlite3
import os

testing = True

def fix_croatian_chars(text):
    chars = {'č': 'c', 'ć': 'c', 'š': 's', 'đ': 'dj', 'ž': 'z'}
    for old, new in chars.items():
        text = text.replace(old, new).replace(old.upper(), new.upper())
    return text

conn = sqlite3.connect('sqldb/gosling2.db')
cur = conn.cursor()

cur.execute("SELECT SourceID, MediaName, SourcePath FROM MediaSources WHERE MediaName LIKE '%č%' OR MediaName LIKE '%ć%' OR MediaName LIKE '%š%' OR MediaName LIKE '%đ%' OR MediaName LIKE '%ž%'")
rows = cur.fetchall()

print(f'Found {len(rows)} songs with Croatian letters')

renamed = 0
for sid, name, path in rows:
    if not path:
        continue
    
    new_name = fix_croatian_chars(name)
    cur.execute('UPDATE MediaSources SET MediaName = ? WHERE SourceID = ?', (new_name, sid))
    
    filename = path.split('\\')[-1]
    new_filename = fix_croatian_chars(filename)
    
    folder = 'Z:/Songs/' + path.split('songs\\')[-1].replace('\\', '/').replace(filename, '')
    old_path = folder + filename
    new_path = folder + new_filename
    
    if testing:
        print(f'Testing: {old_path} -> {new_path}')
        continue
    if os.path.exists(old_path) and old_path != new_path:
        os.rename(old_path, new_path)
        new_db_path = path.replace(filename, new_filename)
        cur.execute('UPDATE MediaSources SET SourcePath = ? WHERE SourceID = ?', (new_db_path, sid))
        renamed += 1

if not testing:
    conn.commit()
conn.close()
print(f'Renamed {renamed} files')