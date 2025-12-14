import sys
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QCoreApplication

# Needed for QTimer??
app = QCoreApplication(sys.argv)

import src.business.services.playback_service
from src.business.services.playback_service import PlaybackService

def verify_crossfade():
    print("Starting verification...")
    
    # 1. Patch dependencies manually where they live in the module
    # We patch the CLASS in the module
    
    with patch("src.business.services.playback_service.QMediaPlayer") as MockPlayerClass, \
         patch("src.business.services.playback_service.QAudioOutput") as MockAudioClass, \
         patch("src.business.services.playback_service.QTimer") as MockTimerClass, \
         patch("src.business.services.settings_manager.SettingsManager") as MockSettingsClass:
        
        # Configure Mocks
        player_mocks = []
        def create_mock_player():
            m = MagicMock()
            m.playbackState.return_value = 0 # Stopped
            player_mocks.append(m)
            return m
        
        MockPlayerClass.side_effect = create_mock_player
        
        timer_mock = MockTimerClass.return_value
        timer_mock.interval.return_value = 50
        
        settings_mock = MockSettingsClass.return_value
        settings_mock.get_crossfade_duration.return_value = 3000
        settings_mock.get_crossfade_enabled.return_value = True
        
        # 2. Instantiate Service
        service = PlaybackService()
        print(f"Service created. Players: {len(service._players)}")
        
        # 3. Setup Playlist
        service.set_playlist(["A.mp3", "B.mp3"])
        
        # 4. Play First Song
        service.play_at_index(0)
        player_A = service._players[0] # Active
        player_B = service._players[1] # Inactive
        
        print(f"Player A (Active) Play called: {player_A.play.called}")
        
        # Mock State: Player A is playing
        # Must match the Class attribute
        player_A.playbackState.return_value = MockPlayerClass.PlaybackState.PlayingState
        
        # 5. Trigger Crossfade
        print("Triggering play_next()...")
        service.play_next()
        
        # 6. Verify Logic
        # Expectation: Player B start called
        print(f"Player B (Incoming) Play called: {player_B.play.called}")
        if not player_B.play.called:
            print("FAILURE: Player B did not start!")
            return
            
        # Expectation: Timer started
        print(f"Timer started: {timer_mock.start.called}")
        if not timer_mock.start.called:
            print("FAILURE: Timer did not start!")
            return
            
        print("SUCCESS: Crossfade init verified.")
        
        # 7. Simulate Timer Tick
        print("Simulating Tick...")
        # Verify initial volumes
        # Outgoing (A) should be Master (assume 0.5)
        # Incoming (B) should be 0
        
        # We need to check setVolume calls.
        # But setVolume is on AudioOutput.
        # We didn't capture AudioOutput mocks easily?
        # Access via service._audio_outputs
        audio_A = service._audio_outputs[0]
        audio_B = service._audio_outputs[1]
        
        print(f"Audio A: {audio_A}, Audio B: {audio_B}")
        
        # Trigger tick
        service._on_crossfade_tick()
        
        print("Tick 1 executed.")
        
        # Check volumes?
        pass

if __name__ == "__main__":
    verify_crossfade()
