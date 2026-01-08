"""Database configuration"""
import os
from pathlib import Path


class DatabaseConfig:
    """Database configuration settings"""
    
    DATABASE_SUBDIR = 'sqldb'
    DATABASE_FILE_NAME = 'gosling2.db'
    
    @classmethod
    def get_database_path(cls) -> str:
        """Get the database file path"""
        base_dir = Path(__file__).parent.parent.parent
        db_dir = base_dir / cls.DATABASE_SUBDIR
        db_dir.mkdir(exist_ok=True)
        return str(db_dir / cls.DATABASE_FILE_NAME)

