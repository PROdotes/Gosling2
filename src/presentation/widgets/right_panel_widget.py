from typing import List, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QSplitter, 
    QStackedWidget, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from .history_drawer import HistoryDrawer
from .side_panel_widget import SidePanelWidget
from .playlist_widget import PlaylistWidget

# --- STYLING CONSTANTS (From Style Guide) ---
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
    }}
    QPushButton:hover {{ border-color: #666; color: #BBB; }}
    QPushButton:checked {{
        background: #111; 
        border: 1px solid {COLOR_ACCENT}; 
        color: {COLOR_ACCENT};
    }}
"""

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
        self.setStyleSheet(f"#RightPanelHeader {{ background: {COLOR_BG_PANEL}; border: none; }}")
        
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
        self.btn_edit.setFixedWidth(140)
        self.btn_edit.setStyleSheet(self.btn_edit.styleSheet() + "font-size: 10pt; letter-spacing: 1px;")
        layout.addWidget(self.btn_edit)
        
        # Add stretch to center SURGERY MODE
        layout.addStretch()
        
        # Righty: Compact
        self.btn_compact = self._create_toggle("[ = ]", self.toggle_compact)
        self.btn_compact.setFixedWidth(40)
        self.btn_compact.setToolTip("Toggle Compact Playlist")
        layout.addWidget(self.btn_compact)


    def _create_toggle(self, text, signal):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setFixedHeight(28)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus) # SAFETY PROTOCOL: No Keyboard Focus
        btn.setStyleSheet(STYLE_BTN_BASE)
        btn.toggled.connect(signal.emit)
        return btn

class RightPanelFooter(QFrame):
    """
    The Command Deck Footer (Transport & Transitions).
    Lives at the bottom of the Right Panel.
    """
    # Signals for the Facade to expose
    transport_command = pyqtSignal(str) # 'play', 'stop', etc
    transition_command = pyqtSignal(str, int) # 'fade', duration_ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100) # Enough for 2 rows comfortably
        self.setObjectName("RightPanelFooter")
        self.setStyleSheet(f"#RightPanelFooter {{ background: {COLOR_BG_PANEL}; border: none; }}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
        # Row 1: Transport
        transport_layout = QHBoxLayout()
        transport_layout.setSpacing(4)
        
        self.btn_prev = self._create_cmd_btn("|<", "prev")
        self.btn_play = self._create_cmd_btn("PLAY", "play")
        self.btn_stop = self._create_cmd_btn("STOP", "stop")
        self.btn_next = self._create_cmd_btn(">|", "next")
        
        for btn in [self.btn_prev, self.btn_play, self.btn_stop, self.btn_next]:
            transport_layout.addWidget(btn)
        
        # Play button gets special color
        self.btn_play.setStyleSheet(STYLE_BTN_BASE.replace(COLOR_TEXT_DIM, "#FFF") + f"QPushButton {{ background: #222; border: 1px solid {COLOR_ACCENT}; color: {COLOR_ACCENT}; }}")

        layout.addLayout(transport_layout)
        
        # Row 2: Transitions
        trans_layout = QHBoxLayout()
        
        self.btn_cut = self._create_cmd_btn("CUT", "cut")
        self.btn_fade = self._create_cmd_btn("FADE", "fade")
        
        # Fade Duration
        self.combo_fade = QComboBox()
        self.combo_fade.addItems(["1s", "2s", "3s", "5s", "10s"])
        self.combo_fade.setCurrentText("3s")
        self.combo_fade.setFixedWidth(60)
        self.combo_fade.setFixedHeight(28)
        self.combo_fade.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Safety
        self.combo_fade.setStyleSheet(f"background: #111; color: {COLOR_ACCENT}; border: 1px solid #333;")
        
        trans_layout.addWidget(self.btn_cut)
        trans_layout.addStretch()
        trans_layout.addWidget(self.btn_fade)
        trans_layout.addWidget(self.combo_fade)
        
        layout.addLayout(trans_layout)

    def _create_cmd_btn(self, text, command_id):
        btn = QPushButton(text)
        btn.setFixedHeight(34)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus) # SAFETY PROTOCOL
        btn.setStyleSheet(STYLE_BTN_BASE)
        
        # Connect depending on type
        if command_id in ['cut', 'fade']:
             btn.clicked.connect(lambda checked, c=command_id: self._on_transition_click(c))
        else:
             btn.clicked.connect(lambda checked, c=command_id: self._on_transport_click(c))
        
        return btn

    def _on_transport_click(self, cmd):
        self.transport_command.emit(cmd)

    def _on_transition_click(self, cmd):
        self._handle_transition(cmd)

    def _handle_transition(self, type_str):
        # Parse duration
        text = self.combo_fade.currentText().replace('s', '')
        try:
            seconds = int(text)
        except:
            seconds = 3
        self.transition_command.emit(type_str, seconds * 1000)

class RightPanelWidget(QWidget):
    """
    The Command Deck.
    Manages the Stack (History, Editor, Playlist) based on Header Toggles.
    Acts as Facade for Signals.
    """
    
    # Public Signals (Facade)
    transport_command = pyqtSignal(str)
    transition_command = pyqtSignal(str, int)
    
    def __init__(self, library_service, metadata_service, renaming_service, duplicate_scanner, settings_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("RightSurgicalPanel")
        self.settings_manager = settings_manager
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Constraint: Prevent collapse of Command Deck (Corridor: 260px - 500px)
        self.setMinimumWidth(270)
        self.setMaximumWidth(500)
        
        # 1. The Header
        self.header = RightPanelHeader()
        self.layout.addWidget(self.header)
        
        # 2. The Vertical Splitter (The Stack)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(7)
        
        # --- Zone 1: History ---
        # TODO: HistoryDrawer doesn't seem to take services yet, just indices. 
        # Ideally it should read from a log service.
        self.history_widget = HistoryDrawer({}, self) 
        self.history_widget.hide() # Default Hidden
        
        # --- Zone 2: Editor ---
        self.editor_widget = SidePanelWidget(
            library_service, metadata_service, renaming_service, duplicate_scanner
        )
        self.editor_widget.hide() # Default Hidden
        
        # --- Zone 3: Playlist ---
        self.playlist_widget = PlaylistWidget()
        self.playlist_widget.setMinimumHeight(150)
        self.playlist_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # FIX: No horizontal scroll
        
        self.splitter.addWidget(self.history_widget)
        self.splitter.addWidget(self.editor_widget)
        self.splitter.addWidget(self.playlist_widget)
        
        # Playlist is the anchor (Item 2)
        # We allow them to collapse but Playlist resists
        self.splitter.setCollapsible(0, True) 
        self.splitter.setCollapsible(1, True) 
        self.splitter.setCollapsible(2, False)
        
        self.layout.addWidget(self.splitter)
        
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
            
    def update_history(self, entries: List[Any]):
        """Updates History Drawer"""
        # TODO: Implement history update logic once HistoryDrawer supports it
        pass

    def set_mode(self, mode: str):
        """Programmatic mode switch"""
        if mode == 'edit':
            self.header.btn_edit.setChecked(True)
        elif mode == 'log':
            self.header.btn_hist.setChecked(True)

    # --- INTERNAL SLOTS ---

    def _on_toggle_history(self, checked):
        self.history_widget.setVisible(checked)
        
    def _on_toggle_editor(self, checked):
        self.editor_widget.setVisible(checked)

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
