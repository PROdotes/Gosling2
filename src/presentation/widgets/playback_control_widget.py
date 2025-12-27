from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QComboBox, QFrame
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from .seek_slider import SeekSlider

class PlaybackControlWidget(QWidget):
    """Widget for playback controls (Play/Pause, Seek, Volume, metadata display)"""
    
    # User Actions
    play_pause_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    volume_changed = pyqtSignal(int)
    seek_request = pyqtSignal(int) # Emitted when slider is dragged

    def __init__(self, playback_service, settings_manager, parent=None) -> None:
        super().__init__(parent)
        self.playback_service = playback_service
        self.settings_manager = settings_manager
        
        # State
        self._playlist_count = 0
        self._is_crossfading = False
        
        self._init_ui()
        self._setup_connections()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        
        # --- LEFT: THE IDENT (Cover & Detail) ---
        self.cover_bay = QFrame()
        self.cover_bay.setFixedSize(80, 80)
        self.cover_bay.setObjectName("CoverBay") # Neon Bordered Frame
        
        ident_layout = QVBoxLayout()
        ident_layout.addWidget(self.cover_bay, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(ident_layout)

        # --- CENTER: THE ENGINE (Title & Transport) ---
        engine_layout = QVBoxLayout()
        engine_layout.setSpacing(4)
        
        # Large Readout
        self.song_label = QLabel("NO MEDIA ARMED")
        self.song_label.setObjectName("LargeSongLabel")
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        engine_layout.addWidget(self.song_label)
        
        # (Transport Buttons Removed T-54)

        
        # Seek Strip
        self.playback_slider = SeekSlider()
        self.playback_slider.setObjectName("PlaybackSeekSlider")
        engine_layout.addWidget(self.playback_slider)
        
        layout.addLayout(engine_layout, 1)

        # --- RIGHT: THE MONITOR (Timers & Metering) ---
        monitor_layout = QVBoxLayout()
        monitor_layout.setSpacing(6)
        
        # Timers (Horizontal Row)
        timers_row = QHBoxLayout()
        self.lbl_time_passed = QLabel("00:00")
        self.lbl_time_passed.setObjectName("PlaybackTimer")
        
        self.lbl_time_remaining = QLabel("- 00:00")
        self.lbl_time_remaining.setObjectName("PlaybackTimer")
        
        timers_row.addWidget(self.lbl_time_passed)
        timers_row.addStretch()
        timers_row.addWidget(self.lbl_time_remaining)
        monitor_layout.addLayout(timers_row)
        
        # Waveform Placeholder (Sleek Frame)
        self.waveform_deck = QFrame()
        self.waveform_deck.setFixedHeight(25)
        self.waveform_deck.setObjectName("WaveformDeck") # Neon Pulse Placeholder
        monitor_layout.addWidget(self.waveform_deck)
        
        # Control Cluster (Volume & Crossfade)
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        
        # Youtube-style Volume (Icon + Slider)
        self.vol_icon = QLabel("🔈")
        self.vol_icon.setObjectName("VolumeIcon")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(70)
        self.volume_slider.setObjectName("VolumeSlider")
        
        controls_row.addWidget(self.vol_icon)
        controls_row.addWidget(self.volume_slider)
        controls_row.addSpacing(10)
        
        monitor_layout.addLayout(controls_row)
        layout.addLayout(monitor_layout)

        self.setStyleSheet("""
            PlaybackControlWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                          stop:0 #111, stop:0.4 #222, 
                                          stop:0.5 #2A2A2A, stop:0.6 #222, 
                                          stop:1 #111);
                border-top: 2px solid #000;
            }
            #LargeSongLabel {
                color: #FF8C00;
                font-family: 'Agency FB';
                font-size: 18pt;
                font-weight: bold;
                letter-spacing: 2px;
                background: transparent;
            }
            #CoverBay {
                border: 2px solid #333;
                background-color: #000;
            }
            #WaveformDeck {
                background-color: #050505;
                border: 1px solid #222;
            }
            #MediaButton, #PlayPauseButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #333, stop:1 #1A1A1A);
                border: 1px solid #111;
                border-radius: 4px;
                color: #FF8C00;
                font-weight: bold;
            }
            #MediaButton:hover, #PlayPauseButton:hover {
                background: #444;
                border: 1px solid #FF8C00;
            }
        """)





    def _setup_connections(self) -> None:
        # UI -> Signals
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)
        self.playback_slider.seekRequested.connect(self.playback_service.seek)
        
        # Service -> UI updates
        self.playback_service.position_changed.connect(self.update_position)
        self.playback_service.duration_changed.connect(self.update_duration)
        
        # Crossfade UI locking (Keep listeners to prevent errors, but do nothing)
        self.playback_service.crossfade_started.connect(self._on_crossfade_started)
        self.playback_service.crossfade_finished.connect(self._on_crossfade_finished)

    def _on_crossfade_started(self):
        self._is_crossfading = True

    def _on_crossfade_finished(self):
        self._is_crossfading = False

    def set_playlist_count(self, count: int) -> None:
        """Update playlist count (No operational effect now)"""
        self._playlist_count = count

    def _update_skip_button_state(self) -> None:
        pass

    def update_play_button_state(self, state) -> None:
        pass

    def update_duration(self, duration) -> None:
        self.playback_slider.updateDuration(duration)
        formatted_time = self._format_time(duration)
        self.lbl_time_remaining.setText(f"-{formatted_time}")

    def update_position(self, position) -> None:
        self.playback_slider.blockSignals(True)
        self.playback_slider.setValue(position)
        self.playback_slider.blockSignals(False)
        
        duration = self.playback_service.get_duration()
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
