import sqlite3
import os


class DBManager:
    DATABASE_SUBDIR = 'sqldb'
    DATABASE_FILE_NAME = 'gosling2.sqlite3'
    DATABASE_NAME = os.path.join(os.path.dirname(__file__), DATABASE_SUBDIR, DATABASE_FILE_NAME)

    def __init__(self):
        db_dir = os.path.join(os.path.dirname(__file__), self.DATABASE_SUBDIR)
        os.makedirs(db_dir, exist_ok=True)
        self.create_schema()

    def create_schema(self):
        """Opens, creates schema, commits, and closes the connection immediately."""
        with sqlite3.connect(self.DATABASE_NAME) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
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
            default_roles = ["Performer", "Composer", "Lyricist", "Producer"]
            cursor.executemany("INSERT OR IGNORE INTO Roles (Name) VALUES (?)", [(r,) for r in default_roles])
            # --- Create the FileContributorRoles Table ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS FileContributorRoles (
                    FileID INTEGER NOT NULL,
                    ContributorID INTEGER NOT NULL,
                    RoleID INTEGER NOT NULL,
                    PRIMARY KEY (FileID, ContributorID, RoleID),
                    FOREIGN KEY (FileID) REFERENCES Files(FileID) ON DELETE CASCADE,
                    FOREIGN KEY (ContributorID) REFERENCES Contributors(ContributorID) ON DELETE CASCADE,
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

    def insert_file_basic(self, file_path):
        """
        Inserts a file path and placeholder data into the Files table.
        Returns True if inserted, or None if it already exists/fails.
        """
        file_title = os.path.basename(file_path)
        try:
            with sqlite3.connect(self.DATABASE_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO Files (Path, Title)
                    VALUES (?, ?)
                """, (file_path, file_title))
                return cursor.lastrowid if cursor.rowcount > 0 else None
        except sqlite3.Error as e:
            print(f"Database error during basic file insert: {e}")
            return None

    def fetch_all_library_data(self):
        with sqlite3.connect(self.DATABASE_NAME) as conn:
            cursor = conn.cursor()
            query = """
                        SELECT F.FileID,
                               GROUP_CONCAT(CASE WHEN R.Name = 'Performer' THEN C.Name END, ', ') AS Artists,
                               F.Title AS Title,
                               F.Duration AS Duration,
                               F.Path AS Path,
                               GROUP_CONCAT(CASE WHEN R.Name = 'Composer' THEN C.Name END, ', ') AS Composers,
                               F.TempoBPM AS BPM
                        FROM Files F
                                 LEFT JOIN FileContributorRoles FCR ON F.FileID = FCR.FileID
                                 LEFT JOIN Contributors C ON FCR.ContributorID = C.ContributorID
                                 LEFT JOIN Roles R ON FCR.RoleID = R.RoleID
                        GROUP BY F.FileID, F.Path, F.Title, F.Duration, F.TempoBPM
                        ORDER BY F.FileID DESC;
                    """
            try:
                cursor.execute(query)
                headers = [description[0] for description in cursor.description]
                data = cursor.fetchall()
                return headers, data
            except sqlite3.Error as e:
                print(f"Database error during basic file insert: {e}")
                return [], []

    def delete_file_by_id(self, file_id):
        """
        Deletes a record from the Files table using its FileID.
        """
        try:
            with sqlite3.connect(self.DATABASE_NAME) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Files WHERE FileID = ?", (file_id,))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error during file deletion: {e}")
            return False

    def fetch_data_for_tree(self, role_name: str):
        """
        Fetches a distinct list of all Contributors who have the :role_name role,
        ordered by SortName.
        Returns: list of (ContributorID, Name)
        """
        try:
            # Use the 'with' statement for automatic connection management
            with sqlite3.connect(self.DATABASE_NAME) as conn:
                cursor = conn.cursor()
                # Select distinct Contributors linked to the 'Performer' role
                query = """
                        SELECT DISTINCT C.ContributorID,
                                        C.Name
                        FROM Contributors C
                                 JOIN FileContributorRoles FCR ON C.ContributorID = FCR.ContributorID
                                 JOIN Roles R ON FCR.RoleID = R.RoleID
                        WHERE R.Name = ?
                        ORDER BY C.SortName ASC
                        """
                cursor.execute(query, (role_name,))
                data = cursor.fetchall()
                return data
        except sqlite3.Error as e:
            # The connection is automatically closed even if an error occurs here
            print(f"Database error during artist fetch: {e}")
            return []

    def update_file_data(self, song):
        """
        Updates the metadata fields for an existing file record using its FileID.
        """
        try:
            # Open connection for transaction (stateless model)
            with sqlite3.connect(self.DATABASE_NAME) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE Files
                    SET Title = ?, Duration = ?, TempoBPM = ?
                    WHERE FileID = ?
                """, (song.title, song.duration, song.bpm, song.file_id))
                cursor.execute("DELETE FROM FileContributorRoles WHERE FileID = ?", (song.file_id,))
                self._sync_contributor_roles(song, conn)
                return True
        except sqlite3.Error as e:
            print(f"Database error during metadata update: {e}")
            return False

    def _sync_contributor_roles(self, song, conn):
        """
        Adds contributors to the database
        """
        cursor = conn.cursor()
        role_map = {
            'performers': 'Performer',
            'composers': 'Composer',
            'lyricists': 'Lyricist',
            'producers': 'Producer'
        }
        for attr, role_name in role_map.items():
            contributors = getattr(song, attr, [])
            if not contributors:
                continue

            # Get RoleID
            cursor.execute("SELECT RoleID FROM Roles WHERE Name = ?", (role_name,))
            role_row = cursor.fetchone()
            if not role_row:
                continue
            role_id = role_row[0]

            for contributor_name in contributors:
                # Insert contributor if not exists
                cursor.execute("""
                    INSERT OR IGNORE INTO Contributors (Name, SortName)
                    VALUES (?, ?)
                """, (contributor_name, contributor_name))
                # Get ContributorID
                cursor.execute("""
                    SELECT ContributorID FROM Contributors WHERE Name = ?
                """, (contributor_name,))
                contributor_row = cursor.fetchone()
                if not contributor_row:
                    continue
                contributor_id = contributor_row[0]

                # Insert into FileContributorRoles
                cursor.execute("""
                    INSERT OR IGNORE INTO FileContributorRoles (FileID, ContributorID, RoleID)
                    VALUES (?, ?, ?)
                """, (song.file_id, contributor_id, role_id))
        return True
