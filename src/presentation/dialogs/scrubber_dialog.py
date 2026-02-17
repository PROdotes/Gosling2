"""
ScrubberDialog - Modal song preview with seek and genre tagging.
Opens on double-click when edit mode is enabled.
"""
from typing import List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QMouseEvent

from ..widgets.glow_factory import GlowButton
from ..widgets.chip_tray_widget import ChipTrayWidget
from ..widgets.waveform_monitor import WaveformMonitor
from ...business.services.playback_service import PlaybackService
from ...business.services.waveform_service import WaveformService


class ScrubberDialog(QDialog):
    """
    Modal dialog for previewing a song with transport controls and genre tagging.
    Uses an isolated PlaybackService instance.
    """
    
    genre_changed = pyqtSignal(list)  # Emits list of genre names when changed
    
    def __init__(self, song, settings_manager,
                 library_service=None, parent=None):
        """
        Args:
            song: Song object with path, artist, title, source_id
            settings_manager: SettingsManager for PlaybackService
            library_service: LibraryService for genre tag management
            parent: Parent widget
        """
        super().__init__(parent)
        self.song = song
        self.settings_manager = settings_manager
        self.library_service = library_service
        
        # Own waveform service — isolated from other consumers
        self.waveform_service = WaveformService(
            settings_manager=settings_manager
        )
        
        self.setWindowTitle("Song Scrubber")
        self.setModal(True)
        self.setMinimumSize(550, 350)
        self.resize(600, 400)
        self.setObjectName("ScrubberDialog")
        
        # Create isolated playback service
        self._playback = PlaybackService(settings_manager)
        
        self._init_ui()
        self._setup_connections()
        self._load_song()
        
        # Position update timer
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(50)  # 20fps
        self._position_timer.timeout.connect(self._update_position)
        self._position_timer.start()
        
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # === Waveform Area (with HUD Readout) ===
        self.waveform = WaveformMonitor(compact=True)
        layout.addWidget(self.waveform)

        # Initialize with current data
        artist = self.song.performers[0] if self.song.performers else 'Unknown artist'
        title = getattr(self.song, 'title', '') or 'Unknown Title'
        self.waveform.set_song_info(artist, title)

        # Update HUD from DB if available
        self._update_hud_from_db()
        
        
        # === Transport Controls ===
        transport_row = QHBoxLayout()
        transport_row.setSpacing(10)
        
        transport_row.addStretch()
        
        self.btn_play = GlowButton("▶")
        self.btn_play.setObjectName("ScrubberPlayButton")
        self.btn_play.setFixedSize(60, 60)
        self.btn_play.setCheckable(True)
        transport_row.addWidget(self.btn_play)
        
        transport_row.addStretch()
        layout.addLayout(transport_row)
        
        # === Genre Chip Tray ===
        genre_container = QFrame()
        genre_container.setObjectName("ScrubberGenreContainer")
        genre_layout = QVBoxLayout(genre_container)
        genre_layout.setContentsMargins(0, 10, 0, 0)
        genre_layout.setSpacing(5)
        
        genre_label = QLabel("Genre")
        genre_label.setObjectName("ScrubberSectionLabel")
        genre_layout.addWidget(genre_label)
        
        self.genre_tray = ChipTrayWidget(
            confirm_removal=False,
            add_tooltip="Add Genre",
            show_add=True
        )
        genre_layout.addWidget(self.genre_tray)
        
        layout.addWidget(genre_container)
        
        # Load existing genres if available
        self._load_genres()
        
    def _setup_connections(self) -> None:
        # Play button
        self.btn_play.toggled.connect(self._on_play_toggled)
        
        # Waveform seeking
        self.waveform.seek_requested.connect(self._on_seek)
        
        # Playback service signals
        self._playback.duration_changed.connect(self._on_duration_changed)
        self._playback.state_changed.connect(self._on_state_changed)
        
        # Genre tray
        self.genre_tray.add_requested.connect(self._on_add_genre)
        self.genre_tray.chip_remove_requested.connect(self._on_remove_genre)
        
        if self.waveform_service:
            self.waveform_service.finished.connect(
                self._on_waveform_finished
            )
            self.waveform_service.error.connect(
                self._on_waveform_error
            )

    def _on_waveform_finished(self, peaks: List[float]):
        print(f"ScrubberDialog: Got {len(peaks)} peaks, sum={sum(peaks):.2f}, max={max(peaks):.2f}")
        self.waveform.set_peaks(peaks)
        self.waveform.update() # Force repaint

    def _on_waveform_error(self, msg: str):
        print(f"ScrubberDialog: Waveform Error: {msg}")

    def _load_song(self) -> None:
        """Load and auto-play the song"""
        path = getattr(self.song, 'path', None)
        if path:
            self._playback.load(path)
            self._playback.play()
            self.btn_play.setChecked(True)
            
            # --- REAL WAVEFORM DATA ---
            self.waveform_service.load_waveform(path)
            
    def _load_genres(self) -> None:
        """Load existing genres into the chip tray"""
        if not self.library_service or not hasattr(self.library_service, 'tag_service'):
            return
            
        tag_service = self.library_service.tag_service
        source_id = getattr(self.song, 'source_id', None) or getattr(self.song, 'file_id', None)
        if not source_id:
            return
            
        try:
            # Get genre tags for this song
            tags = tag_service.get_tags_for_source(source_id, category="Genre")
            for tag in tags:
                tag_id = getattr(tag, 'tag_id', None) or getattr(tag, 'id', None)
                tag_name = getattr(tag, 'tag_name', None) or getattr(tag, 'name', str(tag))
                if tag_id and tag_name:
                    self.genre_tray.add_chip(tag_id, tag_name, zone="genre")
        except Exception as e:
            print(f"ScrubberDialog: Error loading genres: {e}")

    def _update_hud_from_db(self) -> None:
        """Update waveform HUD with fresh data from database"""
        if not self.library_service:
            return

        source_id = getattr(self.song, 'source_id', None) or getattr(self.song, 'file_id', None)
        if not source_id:
            return

        try:
            fresh_song = self.library_service.get_song_by_id(source_id)
            if fresh_song:
                artist = fresh_song.performers[0] if fresh_song.performers else 'Unknown artist'
                title = getattr(fresh_song, 'title', '') or 'Unknown Title'
                self.waveform.set_song_info(artist, title)
        except Exception as e:
            print(f"ScrubberDialog: Error updating HUD from DB: {e}")

    def _on_play_toggled(self, checked: bool) -> None:
        if checked:
            self._playback.play()
            self.btn_play.setText("⏸")
        else:
            self._playback.pause()
            self.btn_play.setText("▶")
            
    def _on_seek(self, ratio: float) -> None:
        duration = self._playback.get_duration()
        if duration > 0:
            position_ms = int(ratio * duration)
            self._playback.seek(position_ms)
            
    def _on_duration_changed(self, duration_ms: int) -> None:
        self.waveform.set_duration(duration_ms)
        self.waveform.set_position(self._playback.get_position() / duration_ms if duration_ms > 0 else 0, self._playback.get_position())
        
    def _on_state_changed(self, state) -> None:
        from PyQt6.QtMultimedia import QMediaPlayer
        is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        
        # Sync button state
        self.btn_play.blockSignals(True)
        self.btn_play.setChecked(is_playing)
        self.btn_play.setText("⏸" if is_playing else "▶")
        self.btn_play.blockSignals(False)
        
    def _update_position(self) -> None:
        """Timer callback, updates position indicator"""
        duration = self._playback.get_duration()
        position = self._playback.get_position()
        
        if duration > 0:
            ratio = position / duration
            self.waveform.set_position(ratio, position)
            
        
    def _on_add_genre(self) -> None:
        """Handle add genre button click"""
        if not self.library_service or not hasattr(self.library_service, 'tag_service'):
            return
            
        # Import here to avoid circular imports
        from ..dialogs.entity_picker_dialog import EntityPickerDialog
        from src.core.picker_config import get_tag_picker_config
        
        source_id = getattr(self.song, 'source_id', None) or getattr(self.song, 'file_id', None)
        tag_service = self.library_service.tag_service
        
        # Get existing genre IDs to exclude
        existing_ids = set()
        for i in range(self.genre_tray.flow_layout.count()):
            widget = self.genre_tray.flow_layout.itemAt(i).widget()
            if hasattr(widget, 'entity_id'):
                existing_ids.add(widget.entity_id)
        
        # Create config with Genre pre-selected
        config = get_tag_picker_config()
        config.default_type = "Genre"
        
        dlg = EntityPickerDialog(
            service_provider=self.library_service,
            config=config,
            exclude_ids=existing_ids,
            parent=self
        )
        
        if dlg.exec():
            selected = dlg.get_selected()
            if selected:
                tag_id = getattr(selected, 'tag_id', None) or getattr(selected, 'id', None)
                tag_name = getattr(selected, 'tag_name', None) or getattr(selected, 'name', str(selected))
                # Add to service
                if source_id and tag_id:
                    tag_service.add_tag_to_source(source_id, tag_id)
                # Add to UI
                if tag_id and tag_name:
                    self.genre_tray.add_chip(tag_id, tag_name, zone="genre")
                self.genre_changed.emit(self.genre_tray.get_names())
                
    def _on_remove_genre(self, entity_id: int, label: str) -> None:
        """Handle genre chip removal"""
        source_id = getattr(self.song, 'source_id', None) or getattr(self.song, 'file_id', None)
        
        if self.library_service and hasattr(self.library_service, 'tag_service') and source_id:
            try:
                self.library_service.tag_service.remove_tag_from_source(source_id, entity_id)
            except Exception as e:
                print(f"ScrubberDialog: Error removing genre: {e}")
                
        self.genre_tray.remove_chip(entity_id)
        self.genre_changed.emit(self.genre_tray.get_names())
        
    def keyPressEvent(self, event) -> None:
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Space:
            # Toggle play/pause
            self.btn_play.toggle()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            # Close dialog
            self.close()
            event.accept()
        elif event.key() == Qt.Key.Key_Plus:
            # Open new tag window
            self._on_add_genre()
            event.accept()
        elif event.key() == Qt.Key.Key_Left:
            # Seek back: 1s if shift, else 10s
            step = 1000 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 10000
            current = self._playback.get_position()
            self._playback.seek(max(0, current - step))
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            # Seek forward: 1s if shift, else 10s
            step = 1000 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 10000
            current = self._playback.get_position()
            duration = self._playback.get_duration()
            if duration > 0:
                self._playback.seek(min(duration, current + step))
            event.accept()
        elif event.key() == Qt.Key.Key_Home:
            # Seek to start
            self._playback.seek(0)
            event.accept()
        elif event.key() == Qt.Key.Key_End:
            # Seek to end
            duration = self._playback.get_duration()
            if duration > 0:
                self._playback.seek(duration)
            event.accept()
        else:
            super().keyPressEvent(event)
            
    def closeEvent(self, event) -> None:
        """Clean up playback and waveform service on close"""
        self._position_timer.stop()
        self._playback.stop()
        self._playback.cleanup()
        self.waveform_service.stop()
        super().closeEvent(event)
