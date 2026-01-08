"""Playback management service"""
from typing import List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from typing import TYPE_CHECKING

import shutil
import tempfile
import os

if TYPE_CHECKING:
    from .settings_manager import SettingsManager


from .settings_manager import SettingsManager
from ...core.vfs import VFS


class PlaybackService(QObject):
    """Service for managing audio playback with crossfade support"""

    # Signals
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    state_changed = pyqtSignal(QMediaPlayer.PlaybackState)

    media_status_changed = pyqtSignal(QMediaPlayer.MediaStatus)
    crossfade_started = pyqtSignal()
    crossfade_finished = pyqtSignal()

    def __init__(self, settings_manager: "SettingsManager") -> None:
        super().__init__()
        self._settings = settings_manager
        
        # Dual Player Architecture ("Ping-Pong")
        self._players: List[QMediaPlayer] = []
        self._audio_outputs: List[QAudioOutput] = []
        
        # Create two players
        for _ in range(2):
            self._create_player_pair()
            
        self._active_index = 0
        
        # Crossfade State
        self._crossfade_timer = QTimer()
        self._crossfade_timer.setInterval(50) # 20fps for volume updates
        self._crossfade_timer.timeout.connect(self._on_crossfade_tick)
        
        self._fading_out_index: Optional[int] = None
        self._fade_start_time = 0
        self._fade_duration = 0
        self._fade_elapsed = 0

        self._playlist: List[str] = []
        self._current_index: int = -1
        
        self._temp_files: List[str] = [] # Track temp copies for cleanup
        
        # Connect signals for the initial active player
        self._connect_signals(self.active_player)

    def _create_player_pair(self) -> None:
        """Create a Player+AudioOutput pair"""
        player = QMediaPlayer()
        audio = QAudioOutput()
        player.setAudioOutput(audio)
        self._players.append(player)
        self._audio_outputs.append(audio)

    @property
    def crossfade_duration(self) -> int:
        """Get crossfade duration in milliseconds"""
        return self._settings.get_crossfade_duration()

    @crossfade_duration.setter
    def crossfade_duration(self, duration_ms: int) -> None:
        """Set crossfade duration in milliseconds"""
        self._settings.set_crossfade_duration(duration_ms)
        
    @property
    def crossfade_enabled(self) -> bool:
        """Get whether crossfade is enabled"""
        return self._settings.get_crossfade_enabled()

    @crossfade_enabled.setter
    def crossfade_enabled(self, enabled: bool) -> None:
        """Set whether crossfade is enabled"""
        self._settings.set_crossfade_enabled(enabled)

    @property
    def active_player(self) -> QMediaPlayer:
        return self._players[self._active_index]
    
    @property
    def active_audio(self) -> QAudioOutput:
        return self._audio_outputs[self._active_index]

    def _connect_signals(self, player: QMediaPlayer) -> None:
        """Connect signals from specific player to service signals"""
        player.positionChanged.connect(self.position_changed.emit)
        player.durationChanged.connect(self.duration_changed.emit)
        player.playbackStateChanged.connect(self.state_changed.emit)
        player.mediaStatusChanged.connect(self.media_status_changed.emit)
        player.mediaStatusChanged.connect(self._handle_media_status)

    def _disconnect_signals(self, player: QMediaPlayer) -> None:
        """Disconnect signals safely"""
        # Disconnect ALL slots to prevent ANY signal leakage
        # This is safe because players are private to this service
        
        def safe_disconnect_all(signal):
            try:
                signal.disconnect()
            except (TypeError, RuntimeError):
                # TypeError if no signals connected, which is fine
                pass

        safe_disconnect_all(player.positionChanged)
        safe_disconnect_all(player.durationChanged)
        safe_disconnect_all(player.playbackStateChanged)
        safe_disconnect_all(player.mediaStatusChanged)

    def _handle_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        """Handle media finishing to auto-play next"""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self._fading_out_index is None: # Only if not inside a fade (which stops explicitly)
                self.play_next()

    # --- Playback Control ---

    def _get_temp_copy(self, file_path: str) -> str:
        """Create a temp copy to avoid file locking"""
        is_virtual = VFS.is_virtual(file_path)
        if not is_virtual and not os.path.exists(file_path):
            return file_path # Fallback
            
        try:
            # Create a unique temp file with same extension
            ext = os.path.splitext(file_path)[1]
            fd, temp_path = tempfile.mkstemp(suffix=ext, prefix="gosling_play_")
            os.close(fd) # Close file descriptor immediately
            
            # Copy content (Handle Physical vs Virtual)
            if is_virtual:
                with open(temp_path, 'wb') as f:
                    f.write(VFS.read_bytes(file_path))
            else:
                shutil.copy2(file_path, temp_path)
                
            self._temp_files.append(temp_path)
            
            # Auto-cleanup old temps if list gets too big (e.g. > 50)
            if len(self._temp_files) > 50:
                oldest = self._temp_files.pop(0)
                try:
                    if os.path.exists(oldest): os.remove(oldest)
                except: pass
                
            return temp_path
        except Exception as e:
            # Fallback to original if copy fails
            print(f"PlaybackService Error copying temp: {e}")
            return file_path

    def load(self, file_path: str) -> None:
        """Load a media file into active player (Hard Load)"""
        # If we load manually, we stop any crossfade
        self._stop_crossfade()
        
        real_source = self._get_temp_copy(file_path)
        self.active_player.setSource(QUrl.fromLocalFile(real_source))

    def play(self) -> None:
        self.active_player.play()

    def pause(self) -> None:
        self.active_player.pause()

    def stop(self) -> None:
        self._stop_crossfade()
        self.active_player.stop()

    def seek(self, position_ms: int) -> None:
        self.active_player.setPosition(position_ms)

    def set_volume(self, volume: float) -> None:
        """Set master volume (0.0 to 1.0)"""
        # Save to settings if needed, or assume caller updates settings
        # Here we just apply it.
        # We need to apply it to players respecting fade state.
        # But actually `SettingsManager` is source of truth? 
        # No, commonly this sets internal state.
        # Let's assume `volume` arg is the Master Volume.
        # We need to store it to calculate fade volumes.
        # Since we don't have a `_master_volume` field yet, let's use Settings or AudioOutput?
        # Better to store it.
        self._settings.set_volume(int(volume * 100))
        self._update_volumes()

    def get_volume(self) -> float:
        return self._settings.get_volume() / 100.0

    def _update_volumes(self) -> None:
        """Update volumes of all players based on Master Volume + Fade State"""
        master = self.get_volume()
        
        if self._fading_out_index is not None:
             # Crossfading
             # Calculate progress 0.0 to 1.0
             progress = self._fade_elapsed / self._fade_duration if self._fade_duration > 0 else 1.0
             progress = max(0.0, min(1.0, progress))
             
             # Outgoing (Fading Out): Master * (1 - progress)
             vol_out = master * (1.0 - progress)
             self._audio_outputs[self._fading_out_index].setVolume(vol_out)
             
             # Incoming (Active): Master * progress
             vol_in = master * progress
             self.active_audio.setVolume(vol_in)
        else:
            # Normal State: Active = Master, Inactive = 0 (or Stopped)
            self.active_audio.setVolume(master)
            # Ensure others are silent (though they should be stopped)
            for i, audio in enumerate(self._audio_outputs):
                if i != self._active_index:
                    audio.setVolume(0)

    def get_position(self) -> int:
        return self.active_player.position()

    def get_duration(self) -> int:
        return self.active_player.duration()

    def get_state(self) -> QMediaPlayer.PlaybackState:
        return self.active_player.playbackState()

    def is_playing(self) -> bool:
        return self.active_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    # --- Playlist & Crossfade Logic ---

    def set_playlist(self, playlist: List[str]) -> None:
        self._playlist = playlist
        self._current_index = -1

    def play_at_index(self, index: int) -> None:
        """Play song at index, deciding between Hard Switch or Crossfade"""
        if not (0 <= index < len(self._playlist)):
            return

        is_sequential = (index == self._current_index + 1)
        
        self._stop_crossfade()
        
        self._current_index = index
        next_path = self._playlist[index]
        self.load(next_path)
        self.play()

    def crossfade_to(self, file_path: str) -> None:
        """Transition to specific file (Crossfade if enabled, else Hard Switch)"""
        
        # Check settings
        if not self._settings.get_crossfade_enabled() or not self.is_playing():
             self.load(file_path)
             self.play()
             return

        duration = self._settings.get_crossfade_duration()
        if duration <= 0:
             self.load(file_path)
             self.play()
             return

        # Start Crossfade (ignoring internal playlist index logic)
        # We pass -1 as index since we are driving this manually from UI
        self._start_crossfade(-1, file_path, duration)

    def play_next(self) -> None:
        """Play next song with Crossfade (Internal Playlist Mode)"""
        if self._current_index >= len(self._playlist) - 1:
            return

        next_index = self._current_index + 1
        next_path = self._playlist[next_index]
        
        # Reuse logic
        self.crossfade_to(next_path)
        # Update internal index if we used it
        self._current_index = next_index

    def _start_crossfade(self, next_index: int, next_path: str, duration_ms: int) -> None:
        """Initialize and start the crossfade sequence"""
        # 1. Identify roles
        outgoing_index = self._active_index
        incoming_index = 1 - outgoing_index # Ping Pong (0->1, 1->0)
        
        # 2. Setup Incoming Player
        incoming_player = self._players[incoming_index]
        
        real_next = self._get_temp_copy(next_path)
        incoming_player.setSource(QUrl.fromLocalFile(real_next))
        
        # 3. Switch "Active" Pointer (UI tracks the NEW song immediately)
        self._active_index = incoming_index
        self._current_index = next_index
        
        # 4. Signal Handover
        self._disconnect_signals(self._players[outgoing_index])
        self._connect_signals(incoming_player)
        
        # 5. Start Incoming (Silent)
        self._fading_out_index = outgoing_index
        self._fade_duration = duration_ms
        self._fade_start_time = 0 # using elapsed
        self._fade_elapsed = 0
        
        # Prepare volumes
        self._update_volumes() # sets In=0, Out=Master
        incoming_player.play()
        
        # 6. Start Timer
        self._crossfade_timer.start()
        self.crossfade_started.emit()

    def _on_crossfade_tick(self) -> None:
        """Timer slot for updating volumes"""
        if self._fading_out_index is None:
            self._stop_crossfade()
            return

        self._fade_elapsed += self._crossfade_timer.interval()
        
        if self._fade_elapsed >= self._fade_duration:
            # Finished
            self._stop_crossfade()
        else:
            self._update_volumes()

    def _stop_crossfade(self) -> None:
        """Finalize crossfade (cleanup outgoing)"""
        was_fading = self._fading_out_index is not None
        self._crossfade_timer.stop()
        
        if self._fading_out_index is not None:
            # Create a hard stop for the outgoing player
            outgoing = self._players[self._fading_out_index]
            outgoing.stop()
            self._fading_out_index = None
            
        # Ensure volumes valid
        self._update_volumes()
        
        if was_fading:
            self.crossfade_finished.emit()

    def play_previous(self) -> None:
        # Hard switch for previous
        if self._current_index > 0:
            self.play_at_index(self._current_index - 1)

    def get_current_index(self) -> int:
        return self._current_index

    def get_playlist(self) -> List[str]:
        return self._playlist

    def cleanup(self) -> None:
        """Clean up resources"""
        if not self._players:
            return

        # Clean temp files
        for tmp in self._temp_files:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except:
                pass
        self._temp_files.clear()

        self._stop_crossfade()
        for player in self._players:
            player.stop()
            player.setSource(QUrl())
            player.deleteLater()
        for audio in self._audio_outputs:
            audio.deleteLater()
        self._players.clear()
        self._audio_outputs.clear()

