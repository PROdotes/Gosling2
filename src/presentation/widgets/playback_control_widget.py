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
        
        # Transport Keys
        transport_layout = QHBoxLayout()
        transport_layout.setSpacing(10)
        
        # Placeholder for 'Previous' button
        self.btn_prev = QPushButton("<<")
        self.btn_prev.setObjectName("MediaButton")
        self.btn_prev.setFixedWidth(50)
        
        self.btn_play_pause = QPushButton("PLAY")
        self.btn_play_pause.setObjectName("BigPlayButton")
        self.btn_play_pause.setFixedWidth(120)
        
        self.btn_next = QPushButton(">>")
        self.btn_next.setObjectName("MediaButton")
        self.btn_next.setFixedWidth(50)
        
        transport_layout.addStretch()
        transport_layout.addWidget(self.btn_prev)
        transport_layout.addWidget(self.btn_play_pause)
        transport_layout.addWidget(self.btn_next)
        transport_layout.addStretch()
        engine_layout.addLayout(transport_layout)
        
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
        
        # Crossfade Selector
        self.combo_crossfade = QComboBox()
        self._setup_crossfade_options()
        self.combo_crossfade.setFixedWidth(80)
        self.combo_crossfade.setObjectName("DeckCombo")
        controls_row.addWidget(self.combo_crossfade)
        
        monitor_layout.addLayout(controls_row)
        layout.addLayout(monitor_layout)

    def _setup_crossfade_options(self):
        self.combo_crossfade.addItem("CUT", 0)
        self.combo_crossfade.addItem("1s", 1000)
        self.combo_crossfade.addItem("2s", 2000)
        self.combo_crossfade.addItem("3s", 3000)
        self.combo_crossfade.addItem("5s", 5000)
        self._sync_crossfade_combo()

    def _sync_crossfade_combo(self):
        """Sync combo box state with service settings"""
        enabled = self.playback_service.crossfade_enabled
        duration = self.playback_service.crossfade_duration
        
        if not enabled:
            # Select 0s (Off)
            index = self.combo_crossfade.findData(0)
            if index >= 0:
                self.combo_crossfade.setCurrentIndex(index)
        else:
            # Select matching duration
            index = self.combo_crossfade.findData(duration)
            if index >= 0:
                self.combo_crossfade.setCurrentIndex(index)
            else:
                # If custom duration not in list, maybe add it or default to something?
                # For now, default to Off if unknown to prevent confusion
                self.combo_crossfade.setCurrentIndex(0)

    def _on_crossfade_combo_changed(self, index):
        """Handle crossfade selection change"""
        duration_ms = self.combo_crossfade.currentData()
        
        if duration_ms == 0:
            self.playback_service.crossfade_enabled = False
        else:
            self.playback_service.crossfade_enabled = True
            self.playback_service.crossfade_duration = duration_ms
            
        # Ensure button state remains consistent
        self._update_skip_button_state()

    def _setup_connections(self) -> None:
        # UI -> Signals
        self.btn_play_pause.clicked.connect(self.play_pause_clicked.emit)
        self.btn_prev.clicked.connect(self.prev_clicked.emit)
        self.btn_next.clicked.connect(self.next_clicked.emit)
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)
        self.playback_slider.seekRequested.connect(self.playback_service.seek)
        
        # Crossfade Toggle
        self.combo_crossfade.currentIndexChanged.connect(self._on_crossfade_combo_changed)
        
        # Service -> UI updates
        # We can connect service signals directly to our update methods here
        # This keeps MainWindow cleaner
        self.playback_service.position_changed.connect(self.update_position)
        self.playback_service.state_changed.connect(self.update_play_button_state)
        self.playback_service.duration_changed.connect(self.update_duration)
        
        # Crossfade UI locking
        self.playback_service.crossfade_started.connect(self._on_crossfade_started)
        self.playback_service.crossfade_finished.connect(self._on_crossfade_finished)

    def _on_crossfade_started(self):
        self._is_crossfading = True
        self._update_skip_button_state()

    def _on_crossfade_finished(self):
        self._is_crossfading = False
        self._update_skip_button_state()

    def set_playlist_count(self, count: int) -> None:
        """Update playlist count to enable/disable controls"""
        self._playlist_count = count
        self._update_skip_button_state()

    def _update_skip_button_state(self) -> None:
        """Skip enabled only if >1 songs AND not crossfading"""
        can_skip = (self._playlist_count > 1) and (not self._is_crossfading)
        self.btn_next.setEnabled(can_skip)

    def update_play_button_state(self, state) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play_pause.setText("PAUSE")
        else:
            self.btn_play_pause.setText("PLAY")

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
