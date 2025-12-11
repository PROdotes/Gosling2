
import pytest
from unittest.mock import MagicMock, patch
from src.data.models import Song
from src.data.repositories.song_repository import SongRepository

class TestSongRepositoryExtra:
    @pytest.fixture
    def repository(self):
        return SongRepository()

    def test_sync_contributor_role_defensive_check(self, repository):
        """Test the defensive check 'if not contributor_row' in sync_contributor_roles"""
        file_id = 1
        song = Song(file_id=file_id, title="Defensive", performers=["Ghost"])
        
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        
        # side_effect for fetchone:
        # 1. RoleID lookup -> returns valid row (id 1)
        # 2. ContributorID lookup -> returns None (simulating failure)
        mock_cursor.fetchone.side_effect = [(1,), None]
        
        with patch.object(repository, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_connection
            
            repository.update(song)
            
            # Verify loop behavior
            calls = mock_cursor.execute.call_args_list
            input_calls = [str(call) for call in calls]
            
            # Check for INSERT OR IGNORE
            has_insert = any("INSERT OR IGNORE" in c for c in input_calls)
            assert has_insert
            
            # Check for SELECT
            has_select = any("SELECT ContributorID" in c for c in input_calls)
            assert has_select
            
            # Check for INSERT INTO song_contributors (Link) - Should be FALSE
            has_link = any("INSERT INTO FileContributorRoles" in c for c in input_calls)
            assert not has_link
