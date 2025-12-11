
import pytest
import unittest
from unittest.mock import MagicMock
from src.business.services.playback_service import PlaybackService

class TestPlaybackServiceMutation:
    @pytest.fixture
    def service(self):
        return PlaybackService()

    def test_initial_state_index(self, service):
        """Kill Mutant: Initial index must be -1, not 0"""
        # If mutated to 0, this will fail
        assert service._current_index == -1
        assert service.get_current_index() == -1

    def test_play_previous_from_index_1(self, service):
        """Kill Mutant: play_previous condition > 0 vs > 1"""
        # Setup playlist with 2 items
        service.set_playlist(["song1.mp3", "song2.mp3"])
        
        # Mock load/play to avoid actual implementation calls failing or needing mocks
        service.load = MagicMock()
        service.play = MagicMock()
        
        # Set index to 1 (second song)
        service._current_index = 1
        
        # Call play_previous
        service.play_previous()
        
        # Should now be 0. 
        # If condition was mutated to index > 1, this would have failed to update (remained 1)
        assert service.get_current_index() == 0
        service.load.assert_called_with("song1.mp3")

    def test_play_next_at_end_boundary(self, service):
        """Kill Mutant: play_next condition len - 1 vs len + 1"""
        # Setup playlist with 2 items
        service.set_playlist(["song1.mp3", "song2.mp3"])
        service._current_index = 1 # Last item
        
        # We need to spy on play_at_index or just verify state doesn't change and no side effects happen.
        # But since play_at_index handles bounds safely, the state wouldn't change anyway even if called.
        # We MUST verify that play_at_index was NOT called to prove the guard clause worked.
        
        # We MUST verify that play_at_index was NOT called to prove the guard clause worked.
        
        with unittest.mock.patch.object(service, 'play_at_index') as mock_play:
             service.play_next()
             mock_play.assert_not_called()
                 
        # If mutated to < len + 1 (2 < 3), guard passes, play_at_index called -> FAILURE (Mutant Killed)
