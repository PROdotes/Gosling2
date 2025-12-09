import sqlite3
import os


class DBManager:
    DATABASE_NAME = 'gosling2.sqlite3'

    def __init__(self):
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
                Duration INTEGER,
                TempoBPM INTEGER
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

            conn.commit()

            row_count = cursor.rowcount
            conn.close()  # CRITICAL: Connection closed immediately

            if row_count > 0:
                return file_title
            else:
                return None

        except sqlite3.Error as e:
            print(f"Database error during basic file insert: {e}")
            return None

    def get_all_files_query_string(self):
        """
        Returns the SQL query string for use with QSqlQueryModel.
        """
        return """
            SELECT
                FileID,
                Path AS 'Path',
                Title AS 'Title',
                Duration AS 'Duration',
                TempoBPM AS 'BPM'
            FROM Files
            ORDER BY FileID DESC
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
