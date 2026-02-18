"""
SpotifyImportDialog 🎵
A two-panel interface for pasting Spotify credit text and previewing structured artists.
"""
from typing import List, Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, 
    QDialogButtonBox, QLabel, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence

from src.presentation.widgets.glow_factory import GlowPlainTextEdit, GlowButton
from src.presentation.widgets.spotify_artist_item_widget import SpotifyArtistItemWidget
from src.utils.spotify_credits_parser import parse_spotify_credits
import src.resources.constants as constants

class SpotifyImportDialog(QDialog):
    """
    Dialog for importing artists from Spotify credits.
    Left: Raw text input (Paste area)
    Right: Preview list with editable rows
    """
    
    def __init__(self, service_provider, current_title: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Spotify Credits for: " + current_title)
        self.resize(1000, 600)
        
        self.services = service_provider
        self.current_title = current_title
        self._parsed_artists: List[Dict] = []
        self._parsed_publishers: List[str] = []
        self._row_widgets: List[SpotifyArtistItemWidget] = []
        
        # Debounce timer for parsing
        self._parse_timer = QTimer(self)
        self._parse_timer.setSingleShot(True)
        self._parse_timer.setInterval(200)
        self._parse_timer.timeout.connect(self._do_parse)
        
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)
        
        # 1. Header
        header = QLabel("Paste Spotify Credits below. We'll extract names and roles.")
        header.setStyleSheet("color: #888; font-style: italic; margin-bottom: 5px;")
        layout.addWidget(header)
        
        # 2. Main Content Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #333; }")
        
        # Left Side: Input
        input_container = QFrame()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 10, 0)
        input_layout.setSpacing(8)
        
        input_label = QLabel("PASTE TEXT")
        input_label.setObjectName("FieldLabel")
        input_label.setStyleSheet("font-size: 10px; font-weight: bold; color: #555; letter-spacing: 1px;")
        input_layout.addWidget(input_label)
        
        self.txt_input = GlowPlainTextEdit()
        self.txt_input.setPlaceholderText("Paste credits block (e.g. from Spotify)...")
        if self.current_title:
            self.txt_input.setToolTip(f"Copying credits for: {self.current_title}")
        input_layout.addWidget(self.txt_input)
        
        splitter.addWidget(input_container)
        
        # Right Side: Preview
        preview_container = QFrame()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(10, 0, 0, 0)
        preview_layout.setSpacing(8)
        
        preview_label = QLabel("PREVIEW & MAP")
        preview_label.setObjectName("FieldLabel")
        preview_label.setStyleSheet("font-size: 10px; font-weight: bold; color: #555; letter-spacing: 1px;")
        preview_layout.addWidget(preview_label)
        
        # Scroll area for rows
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("PreviewScroll")
        self.scroll.setStyleSheet("QScrollArea { border: 1px solid #333; background-color: #1e1e1e; border-radius: 4px; }")
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)
        self.scroll_layout.setSpacing(2)
        
        self.scroll.setWidget(self.scroll_content)
        preview_layout.addWidget(self.scroll)
        
        splitter.addWidget(preview_container)
        
        # Set splitter sizes
        splitter.setSizes([350, 650])
        layout.addWidget(splitter, 1)
        
        # 3. Footer Buttons
        self.btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("Import Artists")
        layout.addWidget(self.btn_box)

    def _connect_signals(self):
        self.txt_input.textChanged.connect(self._on_input_changed)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)
        
        # Ctrl+S to trigger Import
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.accept)

    def _on_input_changed(self):
        """Trigger debounced parse."""
        self._parse_timer.start()

    def _do_parse(self):
        """Perform parsing and update preview from flat tuple stream."""
        text = self.txt_input.toPlainText().strip()
        if not text:
            self._clear_preview()
            return
            
        # 1. Get flat stream of tuples [(value, label), ...]
        stream = parse_spotify_credits(text)
        
        # 2. Process Stream
        detected_title = ""
        publishers = []
        artist_map = {} # {name: [roles]}
        
        for val, label in stream:
            if label == "Title":
                detected_title = val
            elif label == "Publisher":
                publishers.append(val)
            elif label == "Composer" or label == "Lyricist" or label == "Arranger" or label == "Producer":
                if val not in artist_map:
                    artist_map[val] = []
                if label not in artist_map[val]:
                    artist_map[val].append(label)

        # 3. Validation: Reactive Title Check (Moved from loop)
        if detected_title:
            colour = constants.COLOR_AMBER
            if detected_title != self.current_title:
                colour = constants.COLOR_RED
            self.txt_input.setGlowColor(colour)

        # 4. Save results for fetch
        self._parsed_publishers = publishers

        # 5. Prepare Preview Data
        preview_data = []
        for name, roles in artist_map.items():
            preview_data.append({
                "name": name,
                "roles": roles
            })
        for pub in publishers:
            preview_data.append({
                "name": pub,
                "roles": ["Publisher"]
            })
            
        # 6. Update rows
        self._update_preview(preview_data)

    def _clear_preview(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._row_widgets = []

    def _update_preview(self, artists: List[Dict]):
        self._clear_preview()
        
        for artist in artists:
            row = SpotifyArtistItemWidget(
                name=artist["name"],
                roles=artist["roles"],
                service_provider=self.services,
                parent=self.scroll_content
            )
            row.delete_requested.connect(self._remove_row)
            self.scroll_layout.addWidget(row)
            self._row_widgets.append(row)
            
        if not artists:
            empty_lbl = QLabel("No artists found with specified roles.")
            empty_lbl.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scroll_layout.addWidget(empty_lbl)

    def _remove_row(self, row):
        if row in self._row_widgets:
            self._row_widgets.remove(row)
            row.deleteLater()

    def get_result(self) -> (List[Dict], List[str]):
        """Return the finalized artist/role mappings and publishers."""
        artists = []
        for row in self._row_widgets:
            name = row.get_name()
            roles = row.get_roles()
            if name and roles: 
                artists.append({
                    "name": name,
                    "roles": roles,
                    "source": "spotify_import"
                })
        return artists, self._parsed_publishers
