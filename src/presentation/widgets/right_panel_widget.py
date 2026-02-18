from typing import List, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QSplitter, 
    QStackedWidget, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from .history_drawer import HistoryDrawer
from .side_panel_widget import SidePanelWidget
from .playlist_widget import PlaylistWidget
from .glow_factory import GlowButton

# Note: All styling moved to theme.qss - see "RIGHT PANEL WIDGET STYLES" section

class RightPanelHeader(QFrame):
    """
    The Control Center Header for the Right Panel.
    Contains Toggles for [HISTORY] | [EDITOR] | [COMPACT].
    """
    toggle_history = pyqtSignal(bool)
    toggle_editor = pyqtSignal(bool)
    toggle_compact = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setObjectName("RightPanelHeader")
        # Styling via QSS: QFrame#RightPanelHeader
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        
        # Lefty: History
        self.btn_hist = self._create_toggle("[ H ]", self.toggle_history)
        self.btn_hist.setFixedWidth(40)
        self.btn_hist.setToolTip("Toggle Broadcast History")
        layout.addWidget(self.btn_hist)
        
        # Add stretch to push SURGERY MODE to center
        layout.addStretch()
        
        # Center: Editor (Big)
        self.btn_edit = self._create_toggle("[ EDIT MODE ]", self.toggle_editor)
        self.btn_edit.setObjectName("EditModeButton")  # For larger font in QSS
        self.btn_edit.setFixedWidth(140)
        layout.addWidget(self.btn_edit)
        
        # Add stretch to center SURGERY MODE
        layout.addStretch()
        
        # Righty: Compact
        self.btn_compact = self._create_toggle("[ = ]", self.toggle_compact)
        self.btn_compact.setFixedWidth(40)
        self.btn_compact.setToolTip("Toggle Compact Playlist")
        layout.addWidget(self.btn_compact)


    def _create_toggle(self, text, signal):
        btn = GlowButton(text)
        btn.setCheckable(True)
        btn.setProperty("class", "RightPanelToggle")  # For QSS: QPushButton.RightPanelToggle
        btn.toggled.connect(signal.emit)
        return btn



class RightPanelWidget(QWidget):
    """
    The Command Deck.
    Manages the Stack (History, Editor, Playlist) based on Header Toggles.
    Acts as Facade for Signals.
    """
    
    # Public Signals (Facade)
    transport_command = pyqtSignal(str)
    transition_command = pyqtSignal(str, int)
    editor_mode_changed = pyqtSignal(bool)
    
    def __init__(self, library_service, metadata_service, renaming_service, duplicate_scanner, settings_manager, spotify_parsing_service=None, parent=None):
        super().__init__(parent)
        self.setObjectName("RightSurgicalPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.settings_manager = settings_manager
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 6, 8, 8)  # Shifted top 2px up
        self.layout.setSpacing(5)
        
        # Constraint: Prevent collapse of Command Deck (Corridor: 350px - 550px)
        self.setMinimumWidth(350)
        self.setMaximumWidth(550)
        
        # 1. The Header
        self.header = RightPanelHeader()
        self.layout.addWidget(self.header)

        # 1b. The Walled-Off Separator (White line)
        self.layout.addSpacing(1) # Tighter gap
        line = QFrame()
        line.setObjectName("HeaderSeparator")
        line.setFixedHeight(1)
        self.layout.addWidget(line)
        
        # 2. The Vertical Splitter (The Stack)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        
        # --- Zone 1: History ---
        # TODO: HistoryDrawer doesn't seem to take services yet, just indices. 
        # Ideally it should read from a log service.
        self.history_widget = HistoryDrawer({}, self) 
        self.history_widget.setMinimumHeight(100)
        self.history_widget.hide() # Default Hidden
        
        # --- Zone 2: Editor ---
        self.editor_widget = SidePanelWidget(
            library_service, metadata_service, renaming_service, duplicate_scanner, settings_manager, spotify_parsing_service
        )
        # settings_manager is now passed via constructor
        
        self.editor_widget.hide() # Default Hidden
        
        # --- Zone 3: Playlist ---
        self.playlist_widget = PlaylistWidget()
        self.playlist_widget.setMinimumHeight(150)
        self.playlist_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # FIX: No horizontal scroll
        
        self.splitter.addWidget(self.history_widget)
        self.splitter.addWidget(self.editor_widget)
        self.splitter.addWidget(self.playlist_widget)
        
        # Playlist is the anchor (Item 2)
        # History and Editor can't collapse to 0 when visible
        self.splitter.setCollapsible(0, False) 
        self.splitter.setCollapsible(1, False) 
        self.splitter.setCollapsible(2, False)
        
        self.layout.addWidget(self.splitter)

        
        # --- INTERNAL WIRING ---
        
        # Header Toggles -> Visibility
        self.header.toggle_history.connect(self._on_toggle_history)
        self.header.toggle_editor.connect(self._on_toggle_editor)
        self.header.toggle_compact.connect(self._on_toggle_compact)
        
        # Footer removed

        
        # --- STATE RESTORATION ---
        self._restore_state()
        
        # --- STATE PERSISTENCE ---
        # --- STATE PERSISTENCE ---
        self.header.toggle_history.connect(lambda _: self._save_toggles())
        self.header.toggle_editor.connect(lambda _: self._save_toggles())
        self.header.toggle_compact.connect(lambda _: self._save_toggles())
        self.splitter.splitterMoved.connect(self._save_splitter)
        
    # --- FACADE METHODS (PUBLIC API) ---
    
    def update_selection(self, songs: List[Any]):
        """Passes selection to SidePanel (Editor)"""
        if self.editor_widget:
            self.editor_widget.set_songs(songs)

    # --- INTERNAL SLOTS ---

    def _on_toggle_history(self, checked):
        self.history_widget.setVisible(checked)
        
    def _on_toggle_editor(self, checked):
        self.editor_widget.setVisible(checked)
        if checked and self.editor_widget.current_songs:
            self.editor_widget.set_songs(self.editor_widget.current_songs, force=True)
        self.editor_mode_changed.emit(checked)

    def _on_toggle_compact(self, checked):
        # Trigger mini mode on the playlist
        if hasattr(self.playlist_widget, 'set_mini_mode'):
             self.playlist_widget.set_mini_mode(checked)

    def _restore_state(self):
        """Restore Toggles and Splitter from Settings."""
        # 1. Toggles
        toggles = self.settings_manager.get_right_panel_toggles()
        
        # Block signals during restore
        self.header.btn_hist.blockSignals(True)
        self.header.btn_edit.blockSignals(True)
        self.header.btn_compact.blockSignals(True)
        
        hist_on = toggles.get('history', False)
        edit_on = toggles.get('editor', False)
        compact_on = toggles.get('compact', False)
        
        self.header.btn_hist.setChecked(hist_on)
        self.header.btn_edit.setChecked(edit_on)
        self.header.btn_compact.setChecked(compact_on)
        
        self.header.btn_hist.blockSignals(False)
        self.header.btn_edit.blockSignals(False)
        self.header.btn_compact.blockSignals(False)
        
        # Apply Logic Manually
        self._on_toggle_history(hist_on)
        self._on_toggle_editor(edit_on)
        self._on_toggle_compact(compact_on)
        
        # 2. Splitter
        state = self.settings_manager.get_right_panel_splitter_state()
        if state:
            self.splitter.restoreState(state)

    def _save_toggles(self):
        """Save toggle states."""
        state = {
            'history': self.header.btn_hist.isChecked(),
            'editor': self.header.btn_edit.isChecked(),
            'compact': self.header.btn_compact.isChecked()
        }
        self.settings_manager.set_right_panel_toggles(state)

    def _save_splitter(self, pos, index):
        """Save splitter state (debounced by nature of save)."""
        self.settings_manager.set_right_panel_splitter_state(self.splitter.saveState())
