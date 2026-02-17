from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QComboBox, QFrame
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from .seek_slider import SeekSlider
from .waveform_monitor import WaveformMonitor
from .glow_factory import GlowButton
from ...business.services import WaveformService

# Note: All styling moved to theme.qss - see "PLAYBACK CONTROL WIDGET STYLES" section

class PlaybackControlWidget(QWidget):
    """
    Hospital-grade Industrial Deck.
    Combines Ident (Cover), Engine (Transport/Transitions), and Monitor (Seek/Meters).
    """
    
    # Unified Command Signals (Matched to MainWindow handlers)
    transport_command = pyqtSignal(str)      # "play", "stop", "prev", "next"
    transition_command = pyqtSignal(str, int)  # "cut", "fade", (duration_ms)
    
    # Legacy compatibility signals
    play_pause_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    
    volume_changed = pyqtSignal(int)
    seek_request = pyqtSignal(int)

    def __init__(self, playback_service, settings_manager, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PlaybackDeck")
        self.setMinimumHeight(100)
        self.playback_service = playback_service
        self.settings_manager = settings_manager
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._playlist_count = 0
        
        # Own waveform service — isolated from other consumers
        self.waveform_service = WaveformService(
            settings_manager=settings_manager
        )
        
        self._init_ui()
        self._setup_connections()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # --- LEFT: THE IDENT BAY (Volume Control) ---
        self.ident_container = QFrame()
        self.ident_container.setObjectName("PlaybackIdentBay")
        ident_layout = QHBoxLayout(self.ident_container)
        ident_layout.setContentsMargins(0, 0, 0, 0)
        
        self.vol_icon = QLabel("🔈")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("VolumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
        ident_layout.addWidget(self.vol_icon)
        ident_layout.addWidget(self.volume_slider)
        
        layout.addWidget(self.ident_container)

        # --- CENTER: THE ENGINE (Transport Controls) ---
        engine_layout = QVBoxLayout()
        engine_layout.setSpacing(5)
        
        # Row 2: Transport & Transition Controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(5)
        
        # Transport
        self.btn_prev = self._create_cmd_btn("|<", "prev")
        self.btn_play = self._create_cmd_btn("PLAY", "play")
        self.btn_play.setObjectName("PlaybackPlayButton")
        self.btn_play.setCheckable(True)
        
        self.btn_pause = self._create_cmd_btn("PAUSE", "pause")
        self.btn_pause.setCheckable(True)

        self.btn_stop = self._create_cmd_btn("STOP", "stop")
        self.btn_next = self._create_cmd_btn(">|", "next_fade")
        
        # Transitions
        self.combo_fade = QComboBox()
        self.combo_fade.setObjectName("PlaybackFadeCombo")
        self.combo_fade.addItems(["0s", "1s", "2s", "3s", "5s", "10s"])
        
        # Perfection Alignment Hack: Make it editable but read-only to center the text
        self.combo_fade.setEditable(True)
        self.combo_fade.lineEdit().setReadOnly(True)
        self.combo_fade.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combo_fade.lineEdit().setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.combo_fade.lineEdit().setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Click-Anywhere: The combo itself now handles everything
        self.combo_fade.mousePressEvent = lambda e: self.combo_fade.showPopup()
        
        # Center the items in the popup too
        for i in range(self.combo_fade.count()):
            self.combo_fade.setItemData(i, Qt.AlignmentFlag.AlignCenter, Qt.ItemDataRole.TextAlignmentRole)
            
        self.combo_fade.setCurrentText("3s")
        self.combo_fade.setFixedWidth(55) # Tighter fit for [10s]
        self.combo_fade.setFixedHeight(31) # Visual docking sweet spot
        self.combo_fade.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        for w in [self.btn_prev, self.btn_play, self.btn_pause, self.btn_stop, self.btn_next]:
            controls_row.addWidget(w)
        
        controls_row.addSpacing(2) 
        controls_row.addWidget(self.combo_fade)
        
        lbl_xfade = QLabel("FADE")
        lbl_xfade.setObjectName("PlaybackXFadeLabel") # For potential QSS styling
        controls_row.addWidget(lbl_xfade)
            
        engine_layout.addLayout(controls_row)
        layout.addLayout(engine_layout, 2)

        # --- RIGHT: THE MONITOR (Timeline & Volume) ---
        monitor_layout = QVBoxLayout()
        monitor_layout.setSpacing(2)
        
        # Monitor
        self.playback_monitor = WaveformMonitor()
        monitor_layout.addWidget(self.playback_monitor)
        
        # Footer
        footer_row = QHBoxLayout()
        monitor_layout.addLayout(footer_row)
        layout.addLayout(monitor_layout, 3)

        # Styling via QSS - no inline styles

    def _create_cmd_btn(self, text, command_id):
        btn = GlowButton(text)
        btn.setFixedHeight(30)
        btn.setFixedWidth(70)
        btn.setProperty("class", "PlaybackCommand")  # For QSS: QPushButton.PlaybackCommand
        
        if command_id == "next_fade":
            btn.clicked.connect(lambda: self._emit_transition("fade"))
        elif command_id in ["cut", "fade"]:
            btn.clicked.connect(lambda: self._emit_transition(command_id))
        elif command_id == "play":
            # Tape Logic: Direct interception for 'Latched' start/resume
            btn.clicked.connect(lambda: self._handle_play_click())
        elif command_id == "pause":
            btn.clicked.connect(lambda: self._handle_pause_click())
        else:
            btn.clicked.connect(lambda: self.transport_command.emit(command_id))
            
        return btn

    def _handle_play_click(self):
        """Play acts as a latched start/resume. Ignore redundant off-toggles."""
        # Guard: Prevent play toggle if nothing is armed
        has_media = not self.playback_service.active_player.source().isEmpty()
        has_playlist = len(self.playback_service.get_playlist()) > 0
        
        if not has_media and not has_playlist:
            self.btn_play.setChecked(False)
            return

        state = self.playback_service.active_player.playbackState()
        
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setChecked(True)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.btn_play.setChecked(True)
            self.transport_command.emit("play")
        else:
            self.transport_command.emit("play")

    def _handle_pause_click(self):
        """Pause logic: Only valid if actively playing/latched."""
        # Guard: Can't pause if not playing (Tape Deck logic)
        # We check the UI state of 'Play' as the proxy for 'Deck Activated'
        if not self.btn_play.isChecked():
            self.btn_pause.setChecked(False)
            return
            
        self.transport_command.emit("pause")

    def _emit_transition(self, cmd):
        dur_str = self.combo_fade.currentText().rstrip('s')
        try:
            duration_ms = int(float(dur_str) * 1000)
        except ValueError:
            duration_ms = 3000
        self.transition_command.emit(cmd, duration_ms)

    def _setup_connections(self) -> None:
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)
        self.playback_monitor.seek_requested.connect(self._handle_monitor_seek)
        
        # Waveform HUD & Peaks
        self.waveform_service.finished.connect(self.playback_monitor.set_peaks)
        self.waveform_service.error.connect(lambda msg: print(f"Waveform Error: {msg}"))
        
        self.playback_service.position_changed.connect(self.update_position)
        self.playback_service.duration_changed.connect(self.update_duration)
        self.playback_service.state_changed.connect(self._on_state_changed)

    def _handle_monitor_seek(self, ratio: float):
        duration = self.playback_service.get_duration()
        if duration > 0:
            pos_ms = int(ratio * duration)
            self.playback_service.seek(pos_ms)

    def _on_state_changed(self, state):
        """Sync visuals with Tape Recorder states."""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setChecked(True)
            self.btn_pause.setChecked(False)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.btn_play.setChecked(True)
            self.btn_pause.setChecked(True)
        else: # Stopped or Null
            self.btn_play.setChecked(False)
            self.btn_pause.setChecked(False)

    def update_duration(self, duration):
        self.playback_monitor.set_duration(duration)

    def update_position(self, position):
        duration = self.playback_service.get_duration()
        if duration > 0:
            ratio = position / duration
            self.playback_monitor.set_position(ratio, position)
        else:
            self.playback_monitor.set_position(0, position)

    def update_song_label(self, text, path=None):
        """HUD Update: Pass metadata and trigger waveform load."""
        if " - " in text:
            parts = text.split(" - ", 1)
            artist = parts[0]
            # Strip duration from title if present: "Title (04:20)" -> "Title"
            title = parts[1].split(" (")[0]
            self.playback_monitor.set_song_info(artist, title)
        else:
            self.playback_monitor.set_song_info("", text)
            
        if path:
            self.waveform_service.load_waveform(path)

    def _format_time(self, ms: int) -> str:
        seconds = int(ms / 1000)
        minutes = seconds // 60
        seconds %= 60
        return f"{minutes:02d}:{seconds:02d}"

    def set_volume(self, volume: int):
        self.volume_slider.setValue(volume)

    def get_volume(self) -> int:
        return self.volume_slider.value()

    def set_playlist_count(self, count: int) -> None:
        self._playlist_count = count
