from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from .seek_slider import SeekSlider

class PlaybackControlWidget(QWidget):
    """Widget for playback controls (Play/Pause, Seek, Volume, metadata display)"""
    
    # User Actions
    play_pause_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    volume_changed = pyqtSignal(int)
    seek_request = pyqtSignal(int) # Emitted when slider is dragged? SeekSlider handles this directly via player usually.

    def __init__(self, playback_service, settings_manager, parent=None) -> None:
        super().__init__(parent)
        self.playback_service = playback_service
        self.settings_manager = settings_manager
        self._init_ui()
        self._setup_connections()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Song info label
        self.song_label = QLabel("No song loaded")
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        song_font = self.song_label.font()
        song_font.setPointSize(22)
        song_font.setBold(True)
        self.song_label.setFont(song_font)

        # Slider layout
        slider_layout = QHBoxLayout()
        
        self.lbl_time_passed = QLabel("00:00")
        self.lbl_time_passed.setMinimumWidth(40)
        self.lbl_time_passed.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        time_font = self.lbl_time_passed.font()
        time_font.setPointSize(16)
        self.lbl_time_passed.setFont(time_font)
        
        self.playback_slider = SeekSlider()
        self.playback_slider.setPlayer(self.playback_service.player)
        playback_slider_style = """
            QSlider::groove:horizontal {
                height: 30px; 
                background: #404040; 
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 3px; 
                height: 5px;
                border-radius: 6px; 
                background: #5f8a53; 
                margin: -4px 0; 
            }
        """
        self.playback_slider.setStyleSheet(playback_slider_style)
        
        self.lbl_time_remaining = QLabel("- 00:00")
        self.lbl_time_remaining.setMinimumWidth(40)
        self.lbl_time_remaining.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_time_remaining.setFont(time_font)
        
        slider_layout.addWidget(self.lbl_time_passed)
        slider_layout.addWidget(self.playback_slider)
        slider_layout.addWidget(self.lbl_time_remaining)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        self.btn_play_pause = QPushButton("▶ Play")
        self.btn_next = QPushButton(">> Skip")
        media_button_style = """
            QPushButton {
                min-height: 40px; 
                min-width: 80px;
                font-size: 20pt; 
                padding: 5px; 
            }
        """
        self.btn_play_pause.setStyleSheet(media_button_style)
        self.btn_next.setStyleSheet(media_button_style)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        # Don't set default value here - will be set by MainWindow from settings
        self.volume_slider.setMaximumWidth(100)
        
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Volume:"))
        controls_layout.addWidget(self.volume_slider)
        controls_layout.addWidget(self.btn_play_pause)
        controls_layout.addWidget(self.btn_next)
        controls_layout.addStretch()
        
        layout.addWidget(self.song_label)
        layout.addLayout(slider_layout)
        layout.addLayout(controls_layout)

    def _setup_connections(self) -> None:
        # UI -> Signals
        self.btn_play_pause.clicked.connect(self.play_pause_clicked.emit)
        self.btn_next.clicked.connect(self.next_clicked.emit)
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)
        
        # Service -> UI updates
        # We can connect service signals directly to our update methods here
        # This keeps MainWindow cleaner
        self.playback_service.position_changed.connect(self.update_position)
        self.playback_service.state_changed.connect(self.update_play_button_state)
        self.playback_service.player.durationChanged.connect(self.update_duration)

    def update_play_button_state(self, state) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play_pause.setText("|| Pause")
        else:
            self.btn_play_pause.setText("▶ Play")

    def update_duration(self, duration) -> None:
        self.playback_slider.setMaximum(duration)
        formatted_time = self._format_time(duration)
        self.lbl_time_remaining.setText(f"-{formatted_time}")

    def update_position(self, position) -> None:
        self.playback_slider.blockSignals(True)
        self.playback_slider.setValue(position)
        self.playback_slider.blockSignals(False)
        
        duration = self.playback_service.player.duration()
        self.lbl_time_passed.setText(self._format_time(position))
        
        remaining = max(0, duration - position)
        self.lbl_time_remaining.setText(f"- {self._format_time(remaining)}")

    def update_song_label(self, text) -> None:
        self.song_label.setText(text)

    def _format_time(self, ms: int) -> str:
        seconds = int(ms / 1000)
        minutes = seconds // 60
        seconds %= 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def set_volume(self, volume: int) -> None:
        """Set volume slider value"""
        self.volume_slider.setValue(volume)
    
    def get_volume(self) -> int:
        """Get current volume slider value"""
        return self.volume_slider.value()
