import sqlite3
import os


class DBManager:
    DATABASE_SUBDIR = 'sqldb'
    DATABASE_FILE_NAME = 'gosling2.sqlite3'
    DATABASE_NAME = os.path.join(os.path.dirname(__file__), DATABASE_SUBDIR, DATABASE_FILE_NAME)

    def __init__(self):
        os.makedirs(self.DATABASE_SUBDIR, exist_ok=True)
        self.create_schema()

    def create_schema(self):
        """Opens, creates schema, commits, and closes the connection immediately."""
        conn = sqlite3.connect(self.DATABASE_NAME)
        cursor = conn.cursor()

        # --- Create the Files Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Files (
                FileID INTEGER PRIMARY KEY,
                Path TEXT NOT NULL UNIQUE,
                Title TEXT NOT NULL,
                Duration REAL,
                TempoBPM INTEGER
            );
        """)
        # --- Create the Contributors Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Contributors (
                ContributorID INTEGER PRIMARY KEY,
                Name TEXT NOT NULL UNIQUE,
                SortName TEXT
            );
        """)
        # --- Create the Roles Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Roles (
                RoleID INTEGER PRIMARY KEY,
                Name TEXT NOT NULL UNIQUE
            );
        """)
        # --- INITIAL ROLE INSERTION (Crucial for first run) ---
        cursor.execute("INSERT OR IGNORE INTO Roles (Name) VALUES ('Performer')")
        cursor.execute("INSERT OR IGNORE INTO Roles (Name) VALUES ('Composer')")
        cursor.execute("INSERT OR IGNORE INTO Roles (Name) VALUES ('Lyricist')")
        cursor.execute("INSERT OR IGNORE INTO Roles (Name) VALUES ('Producer')")
        # --- Create the FileContributorRoles Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FileContributorRoles (
                FileID INTEGER NOT NULL,
                ContributorID INTEGER NOT NULL,
                RoleID INTEGER NOT NULL,
                PRIMARY KEY (FileID, ContributorID, RoleID),
                FOREIGN KEY (FileID) REFERENCES Files(FileID),
                FOREIGN KEY (ContributorID) REFERENCES Contributors(ContributorID),
                FOREIGN KEY (RoleID) REFERENCES Roles(RoleID)
            );
        """)
        # --- Create the GroupMembers Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS GroupMembers (
                GroupID INTEGER NOT NULL,
                MemberID INTEGER NOT NULL,
                PRIMARY KEY (GroupID, MemberID),
                FOREIGN KEY (GroupID) REFERENCES Contributors(ContributorID),
                FOREIGN KEY (MemberID) REFERENCES Contributors(ContributorID)
            );
        """)

        conn.commit()
        conn.close()  # CRITICAL: Connection closed immediately

    def insert_file_basic(self, file_path):
        """
        Inserts a file path and placeholder data into the Files table.
        Returns the title if inserted, or None if it already exists/fails.
        """
        try:
            file_title = os.path.basename(file_path)

            # Open connection for transaction
            conn = sqlite3.connect(self.DATABASE_NAME)
            cursor = conn.cursor()

            # Insert or IGNORE the new file.
            cursor.execute("""
                INSERT OR IGNORE INTO Files (Path, Title, Duration, TempoBPM)
                VALUES (?, ?, ?, ?)
            """, (file_path, file_title, 0, 0))

            file_id = cursor.lastrowid
            conn.commit()

            row_count = cursor.rowcount
            conn.close()  # CRITICAL: Connection closed immediately

            if row_count > 0:
                return file_id
            else:
                return None

        except sqlite3.Error as e:
            print(f"Database error during basic file insert: {e}")
            return None

    def get_all_files_query_string(self):
        return """
               SELECT F.FileID, \
                      GROUP_CONCAT(C.Name, ', ') AS Artists, \
                      F.Path                     AS Path, \
                      F.Title                    AS Title, \
                      F.Duration                 AS Duration, \
                      F.TempoBPM                 AS BPM
               FROM Files F
                        LEFT JOIN FileContributorRoles FCR ON F.FileID = FCR.FileID
                        LEFT JOIN Contributors C ON FCR.ContributorID = C.ContributorID
                        LEFT JOIN Roles R ON FCR.RoleID = R.RoleID
               WHERE R.Name = 'Performer' \
                  OR R.RoleID IS NULL
               GROUP BY F.FileID, F.Path, F.Title, F.Duration, F.TempoBPM
               ORDER BY F.FileID DESC; \
               """

    def delete_file_by_id(self, file_id):
        """
        Deletes a record from the Files table using its FileID.
        """
        try:
            # Open connection for transaction
            conn = sqlite3.connect(self.DATABASE_NAME)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM Files WHERE FileID = ?", (file_id,))
            conn.commit()

            deleted_count = cursor.rowcount
            conn.close()  # CRITICAL: Connection closed immediately

            return deleted_count > 0

        except sqlite3.Error as e:
            print(f"Database error during file deletion: {e}")
            return False

    def update_file_metadata(self, file_id, title, duration, bpm, tags_to_update):
        """
        Updates the metadata fields for an existing file record using its FileID.
        """
        conn = None
        try:
            # Open connection for transaction (stateless model)
            conn = sqlite3.connect(self.DATABASE_NAME)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE Files
                SET Title = ?, Duration = ?, TempoBPM = ?
                WHERE FileID = ?
            """, (title, duration, bpm, file_id))

            self._clear_contributor_links(file_id, conn)
            self.insert_contributor_roles(file_id, tags_to_update, conn)
            conn.commit()
            updated_count = cursor.rowcount
            if updated_count > 0:
                print("Metadata updated successfully.")
                return True
            else:
                print("No rows updated.")
                return False

        except sqlite3.Error as e:
            print(f"Database error during metadata update: {e}")
            if conn: conn.rollback()
            return False
        finally:
            if conn: conn.close()

    def _get_or_create_id(self, conn, table, id_col, name_col, name, other_col=None, other_val=None):
        """Internal helper to get an ID or create a new row in a simple lookup table."""
        cursor = conn.cursor()

        # 1. Try to find existing ID
        cursor.execute(f"SELECT {id_col} FROM {table} WHERE {name_col} = ?", (name,))
        result = cursor.fetchone()
        if result:
            return result[0]

        # 2. If not found, insert new row
        if other_col and other_val is not None:
            # For Contributors (which has Name and SortName)
            cursor.execute(f"INSERT INTO {table} ({name_col}, {other_col}) VALUES (?, ?)", (name, other_val))
        else:
            # For Roles (which only has Name)
            cursor.execute(f"INSERT INTO {table} ({name_col}) VALUES (?)", (name,))

        # 3. Return the ID of the newly inserted row
        return cursor.lastrowid

    def _clear_contributor_links(self, file_id, conn):
        """Removes all entries for a specific FileID from the FileContributorRoles table."""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM FileContributorRoles WHERE FileID = ?", (file_id,))
        # Do NOT commit here; the calling method handles the transaction commit.
        return cursor.rowcount

    def insert_contributor_roles(self, file_id, tags, conn):
        """
        Processes a dictionary of tags (e.g., {'Performer': ['Pink'], 'Composer': ['Alecia...']})
        and links them to the FileID.
        """
        # Define mappings from common tags to canonical roles
        role_mappings = {
            'TPE1': 'Performer',  # Primary Artist/Performer
            'TCOM': 'Composer',  # Composer
            'TOLY': 'Lyricist', #Original lyricist
            'TIT1': 'Group',  # Content Group/Part of a Set
        }

        processed_count = 0

        for tag_key, role_name in role_mappings.items():
            if tag_key in tags and tags[tag_key]:
                # Assumes tags are a list, like ['Artist Name', 'Other Artist']
                names = tags[tag_key] if isinstance(tags[tag_key], list) else [tags[tag_key]]

                for name in names:
                    name = str(name).strip()
                    if not name:
                        continue

                    # Simple sort name for now (full logic can be added later)
                    sort_name = name.upper()

                    # Get or create Contributor and Role IDs
                    contributor_id = self._get_or_create_id(
                        conn, 'Contributors', 'ContributorID', 'Name', name,
                        other_col='SortName', other_val=sort_name
                    )
                    role_id = self._get_or_create_id(
                        conn, 'Roles', 'RoleID', 'Name', role_name
                    )

                    # Link them in the join table
                    conn.cursor().execute("""
                                          INSERT
                                          OR IGNORE INTO FileContributorRoles 
                        (FileID, ContributorID, RoleID) VALUES (?, ?, ?)
                                          """, (file_id, contributor_id, role_id))
                    processed_count += 1

        return True if processed_count > 0 else None
