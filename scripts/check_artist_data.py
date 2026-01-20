
import sqlite3
import os

db_path = r"c:\Users\glazb\PycharmProjects\gosling2\sqldb\gosling2.db"

if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("--- ArtistNames for Gabriel Janković or Gustavo Stitch ---")
query = """
    SELECT an.NameID, an.DisplayName, an.IsPrimaryName, an.OwnerIdentityID, i.IdentityType 
    FROM ArtistNames an 
    JOIN Identities i ON an.OwnerIdentityID = i.IdentityID 
    WHERE DisplayName LIKE '%Gabriel Janković%' OR DisplayName LIKE '%Gustavo Stitch%'
"""
cursor.execute(query)
for row in cursor.fetchall():
    print(f"NameID: {row[0]}, Name: {row[1]}, Primary: {row[2]}, IdentityID: {row[3]}, Type: {row[4]}")

print("\n--- GroupMemberships involving these identities ---")
query = """
    SELECT gm.MembershipID, gm.GroupIdentityID, gm.MemberIdentityID, gm.CreditedAsNameID, an_g.DisplayName, an_m.DisplayName, an_c.DisplayName
    FROM GroupMemberships gm
    JOIN ArtistNames an_g ON gm.GroupIdentityID = an_g.OwnerIdentityID AND an_g.IsPrimaryName = 1
    JOIN ArtistNames an_m ON gm.MemberIdentityID = an_m.OwnerIdentityID AND an_m.IsPrimaryName = 1
    LEFT JOIN ArtistNames an_c ON gm.CreditedAsNameID = an_c.NameID
    WHERE an_g.DisplayName LIKE '%Gabriel Janković%' OR an_g.DisplayName LIKE '%Gustavo Stitch%'
       OR an_m.DisplayName LIKE '%Gabriel Janković%' OR an_m.DisplayName LIKE '%Gustavo Stitch%'
"""
cursor.execute(query)
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Group: {row[4]} (ID:{row[1]}), Member: {row[5]} (ID:{row[2]}), CreditedAs: {row[6]} (NameID:{row[3]})")

conn.close()
