from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QComboBox, QFrame
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from .seek_slider import SeekSlider
from .glow_factory import GlowButton

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
        self.playback_service = playback_service
        self.settings_manager = settings_manager
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._playlist_count = 0
        
        self._init_ui()
        self._setup_connections()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # --- LEFT: THE IDENT BAY (Album Art) ---
        ident_layout = QVBoxLayout()
        ident_layout.setSpacing(5)
        
        # Cover Placeholder
        self.cover_bay = QFrame()
        self.cover_bay.setObjectName("CoverBay")
        self.cover_bay.setFixedSize(60, 60)
        ident_layout.addWidget(self.cover_bay)
        
        # Song Name (Compact)
        self.lbl_song = QLabel("NO MEDIA ARMED")
        self.lbl_song.setObjectName("LargeSongLabel")
        ident_layout.addWidget(self.lbl_song)
        
        layout.addLayout(ident_layout, 1)

        # --- CENTER: THE ENGINE (Transport Controls) ---
        engine_layout = QVBoxLayout()
        engine_layout.setSpacing(5)
        
        # Row 1: The readout (moved to ident_layout)
        
        # Row 2: Transport & Transition Controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(5)
        
        # Transport
        self.btn_prev = self._create_cmd_btn("|<", "prev")
        self.btn_play = self._create_cmd_btn("PLAY", "play")
        self.btn_play.setObjectName("PlaybackPlayButton")  # Special amber styling
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
        
        for w in [self.btn_prev, self.btn_play, self.btn_stop, self.btn_next]:
            controls_row.addWidget(w)
        
        controls_row.addSpacing(2) # Visual docking (closer to skip)
        controls_row.addWidget(self.combo_fade)
        
        lbl_xfade = QLabel("X-FADE:")
        lbl_xfade.setObjectName("PlaybackXFadeLabel") # For potential QSS styling
        controls_row.addWidget(lbl_xfade)
            
        engine_layout.addLayout(controls_row)
        layout.addLayout(engine_layout, 2)

        # --- RIGHT: THE MONITOR (Timeline & Volume) ---
        monitor_layout = QVBoxLayout()
        monitor_layout.setSpacing(2)
        
        # Seek Strip
        self.playback_slider = SeekSlider()
        monitor_layout.addWidget(self.playback_slider)
        
        # Timers and Volume
        footer_row = QHBoxLayout()
        self.lbl_time_passed = QLabel("00:00")
        self.lbl_time_remaining = QLabel("- 00:00")
        self.lbl_time_passed.setObjectName("PlaybackTimer")
        self.lbl_time_remaining.setObjectName("PlaybackTimer")
        
        self.vol_icon = QLabel("🔈")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("VolumeSlider")  # For QSS styling
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(80)
        
        footer_row.addWidget(self.lbl_time_passed)
        footer_row.addStretch()
        footer_row.addWidget(self.lbl_time_remaining)
        footer_row.addWidget(self.vol_icon)
        footer_row.addWidget(self.volume_slider)
        
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
        else:
            btn.clicked.connect(lambda: self.transport_command.emit(command_id))
            
        return btn

    def _emit_transition(self, cmd):
        dur_str = self.combo_fade.currentText().rstrip('s')
        try:
            duration_ms = int(float(dur_str) * 1000)
        except ValueError:
            duration_ms = 3000
        self.transition_command.emit(cmd, duration_ms)

    def _setup_connections(self) -> None:
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)
        self.playback_slider.seekRequested.connect(self.playback_service.seek)
        
        self.playback_service.position_changed.connect(self.update_position)
        self.playback_service.duration_changed.connect(self.update_duration)
        self.playback_service.state_changed.connect(self._on_state_changed)

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("PAUSE")
        else:
            self.btn_play.setText("PLAY")

    def update_duration(self, duration):
        self.playback_slider.updateDuration(duration)
        self.lbl_time_remaining.setText(f"- {self._format_time(duration)}")

    def update_position(self, position):
        self.playback_slider.blockSignals(True)
        self.playback_slider.setValue(position)
        self.playback_slider.blockSignals(False)
        self.lbl_time_passed.setText(self._format_time(position))
        
        duration = self.playback_service.get_duration()
        remaining = max(0, duration - position)
        self.lbl_time_remaining.setText(f"- {self._format_time(remaining)}")

    def update_song_label(self, text):
        self.lbl_song.setText(text)

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
