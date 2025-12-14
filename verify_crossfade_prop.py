import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

try:
    from src.business.services.playback_service import PlaybackService
    s = PlaybackService()
    print("Has crossfade_duration:", hasattr(s, "crossfade_duration"))
    print("Has active_player:", hasattr(s, "active_player"))
    print("Crossfade Prop:", getattr(PlaybackService, "crossfade_duration", "MISSING_ON_CLASS"))
except Exception as e:
    print(f"Error: {e}")
