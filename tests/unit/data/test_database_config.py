import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.data.database_config import DatabaseConfig

class TestDatabaseConfig:
    def test_get_database_path(self):
        # Mock Path to control returned paths and mkdir behavior
        with patch('src.data.database_config.Path') as MockPath:
            # Setup a mock chain for Path(__file__).parent.parent.parent
            mock_file_path = MagicMock()
            MockPath.return_value = mock_file_path
            
            mock_parent1 = MagicMock()
            mock_file_path.parent = mock_parent1
            
            mock_parent2 = MagicMock()
            mock_parent1.parent = mock_parent2
            
            mock_base_dir = MagicMock()
            mock_parent2.parent = mock_base_dir
            
            # Mock the database directory joining
            mock_db_dir = MagicMock()
            mock_base_dir.__truediv__.return_value = mock_db_dir
            
            # Mock the final file path joining
            mock_final_path = MagicMock()
            mock_db_dir.__truediv__.return_value = mock_final_path
            mock_final_path.__str__.return_value = "/path/to/sqldb/gosling2.db"
            
            # Call the method
            result = DatabaseConfig.get_database_path()
            
            # Assertions
            mock_base_dir.__truediv__.assert_called_with(DatabaseConfig.DATABASE_SUBDIR)
            mock_db_dir.mkdir.assert_called_with(exist_ok=True)
            mock_db_dir.__truediv__.assert_called_with(DatabaseConfig.DATABASE_FILE_NAME)
            assert result == "/path/to/sqldb/gosling2.db"
