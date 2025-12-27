from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QComboBox, QFrame
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from .seek_slider import SeekSlider

# --- STYLING CONSTANTS (Matched to Hospital/Industrial Spec) ---
COLOR_ACCENT = "#FF8C00"
COLOR_BG_PANEL = "#1A1A1A"
COLOR_BG_HEADER = "#2A2A2A"
COLOR_TEXT_DIM = "#888888"

STYLE_BTN_BASE = f"""
    QPushButton {{
        background: {COLOR_BG_HEADER}; 
        border: 1px solid #333; 
        color: {COLOR_TEXT_DIM}; 
        font-weight: bold;
        font-family: 'Bahnschrift Condensed', 'Arial Narrow';
        font-size: 10pt;
    }}
    QPushButton:hover {{ border-color: #666; color: #BBB; }}
    QPushButton:pressed {{ background: #111; }}
"""

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
        self.playback_service = playback_service
        self.settings_manager = settings_manager
        self._playlist_count = 0
        
        self._init_ui()
        self._setup_connections()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        
        # --- LEFT: THE IDENT (Metadata & Cover) ---
        self.cover_bay = QFrame()
        self.cover_bay.setFixedSize(60, 60)
        self.cover_bay.setObjectName("CoverBay")
        layout.addWidget(self.cover_bay)

        # --- CENTER: THE ENGINE (Transport + Transitions) ---
        engine_layout = QVBoxLayout()
        engine_layout.setSpacing(4)
        
        # Row 1: The readout
        self.song_label = QLabel("NO MEDIA ARMED")
        self.song_label.setObjectName("LargeSongLabel")
        engine_layout.addWidget(self.song_label)
        
        # Row 2: Transport & Transition Controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(6)
        
        # Transport
        self.btn_prev = self._create_cmd_btn("|<", "prev")
        self.btn_play = self._create_cmd_btn("PLAY", "play")
        self.btn_stop = self._create_cmd_btn("STOP", "stop")
        self.btn_next = self._create_cmd_btn(">|", "next_fade")
        
        # Transitions
        self.combo_fade = QComboBox()
        self.combo_fade.addItems(["0s", "1s", "2s", "3s", "5s", "10s"])
        self.combo_fade.setCurrentText("3s")
        self.combo_fade.setFixedWidth(60)
        self.combo_fade.setFixedHeight(30)
        self.combo_fade.setStyleSheet(f"background: #111; color: {COLOR_ACCENT}; border: 1px solid #333;")
        
        for w in [self.btn_prev, self.btn_play, self.btn_stop, self.btn_next]:
            controls_row.addWidget(w)
        
        controls_row.addSpacing(20) # Separation
        
        controls_row.addWidget(QLabel("X-FADE:"))
        controls_row.addWidget(self.combo_fade)
            
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
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(80)
        
        footer_row.addWidget(self.lbl_time_passed)
        footer_row.addStretch()
        footer_row.addWidget(self.lbl_time_remaining)
        footer_row.addSpacing(15)
        footer_row.addWidget(self.vol_icon)
        footer_row.addWidget(self.volume_slider)
        
        monitor_layout.addLayout(footer_row)
        layout.addLayout(monitor_layout, 3)

        self.setStyleSheet(f"""
            PlaybackControlWidget {{
                background-color: #0A0A0A;
                border: none;
            }}
            #LargeSongLabel {{
                color: {COLOR_ACCENT};
                font-family: 'Bahnschrift Condensed';
                font-size: 14pt;
                font-weight: bold;
            }}
            #CoverBay {{
                border: 2px solid #333;
                background-color: #000;
            }}
            #PlaybackTimer {{
                color: #666;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
            }}
        """)

    def _create_cmd_btn(self, text, command_id):
        btn = QPushButton(text)
        btn.setFixedHeight(30)
        btn.setFixedWidth(70)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setStyleSheet(STYLE_BTN_BASE)
        if command_id == "play":
            btn.setStyleSheet(STYLE_BTN_BASE + f"QPushButton {{ color: {COLOR_ACCENT}; border-color: {COLOR_ACCENT}; }}")
        
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
        self.song_label.setText(text)

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
