"""Playback management service"""
from typing import List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput


class PlaybackService(QObject):
    """Service for managing audio playback"""

    # Signals
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    state_changed = pyqtSignal(QMediaPlayer.PlaybackState)
    media_status_changed = pyqtSignal(QMediaPlayer.MediaStatus)

    def __init__(self) -> None:
        super().__init__()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Connect internal signals
        self.player.positionChanged.connect(self.position_changed.emit)
        self.player.durationChanged.connect(self.duration_changed.emit)
        self.player.playbackStateChanged.connect(self.state_changed.emit)
        self.player.mediaStatusChanged.connect(self.media_status_changed.emit)

        self._playlist: List[str] = []
        self._current_index: int = -1

    def load(self, file_path: str) -> None:
        """Load a media file"""
        self.player.setSource(QUrl.fromLocalFile(file_path))

    def play(self) -> None:
        """Start playback"""
        self.player.play()

    def pause(self) -> None:
        """Pause playback"""
        self.player.pause()

    def stop(self) -> None:
        """Stop playback"""
        self.player.stop()

    def seek(self, position_ms: int) -> None:
        """Seek to a position in milliseconds"""
        self.player.setPosition(position_ms)

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)"""
        self.audio_output.setVolume(volume)

    def get_volume(self) -> float:
        """Get current volume"""
        return self.audio_output.volume()

    def get_position(self) -> int:
        """Get current position in milliseconds"""
        return self.player.position()

    def get_duration(self) -> int:
        """Get duration in milliseconds"""
        return self.player.duration()

    def get_state(self) -> QMediaPlayer.PlaybackState:
        """Get current playback state"""
        return self.player.playbackState()

    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    # Playlist management
    def set_playlist(self, playlist: List[str]) -> None:
        """Set the current playlist"""
        self._playlist = playlist
        self._current_index = -1

    def play_at_index(self, index: int) -> None:
        """Play song at specific index in playlist"""
        if 0 <= index < len(self._playlist):
            self._current_index = index
            self.load(self._playlist[index])
            self.play()

    def play_next(self) -> None:
        """Play next song in playlist"""
        if self._current_index < len(self._playlist) - 1:
            self.play_at_index(self._current_index + 1)

    def play_previous(self) -> None:
        """Play previous song in playlist"""
        if self._current_index > 0:
            self.play_at_index(self._current_index - 1)

    def get_current_index(self) -> int:
        """Get current playlist index"""
        return self._current_index

    def get_playlist(self) -> List[str]:
        """Get current playlist"""
        return self._playlist

    def cleanup(self) -> None:
        """Clean up resources before shutdown"""
        # Stop playback if player exists
        if self.player:
            self.stop()
        
        # Disconnect all signals to prevent issues during cleanup
        if self.player:
            try:
                self.player.positionChanged.disconnect(self.position_changed.emit)
                self.player.durationChanged.disconnect(self.duration_changed.emit)
                self.player.playbackStateChanged.disconnect(self.state_changed.emit)
                self.player.mediaStatusChanged.disconnect(self.media_status_changed.emit)
            except (TypeError, RuntimeError):
                # Signals may already be disconnected
                pass
            
            # Clear the media source to release file handles
            self.player.setSource(QUrl())
        
        # Delete the audio output and player
        if self.audio_output:
            self.audio_output.deleteLater()
            self.audio_output = None
        
        if self.player:
            self.player.deleteLater()
            self.player = None

