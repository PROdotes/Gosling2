from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
import os

from ..widgets.glow.button import GlowButton
from ...core import yellberus
from ...resources import constants
from ...core.pattern_engine import PatternEngine

class FilenameParserDialog(QDialog):
    """
    Dialog to parse metadata from filenames using custom patterns.
    T-107: Filename -> Metadata Parser.
    """
    
    def __init__(self, selected_songs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parse Metadata from Filename")
        self.resize(1000, 600)
        self.selected_songs = selected_songs
        
        # We only work with the first ~50 songs for preview performance
        self.preview_songs = selected_songs[:50]
        
        # State
        self.current_pattern = "{Artist} - {Title}"
        self.parsed_results = {} # {song_source_id: {field: value}}
        
        self._init_ui()
        self._on_pattern_changed(self.current_pattern) # Initial parse

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 1. Header & Instructions
        header_lbl = QLabel("Extract metadata from filenames using patterns.")
        header_lbl.setStyleSheet("color: #FFC66D; font-size: 14px; font-weight: bold;")
        layout.addWidget(header_lbl)
        
        # Dynamic Token List from Engine
        tokens = ", ".join(PatternEngine.TOKENS)
        instr_lbl = QLabel(
            f"Available tokens: {tokens}, {{Ignore}}\n"
            "Use {Ignore} to skip unwanted parts (e.g. track numbers, 'Official Video', etc)."
        )
        instr_lbl.setStyleSheet("color: #888888;")
        layout.addWidget(instr_lbl)
        
        # 2. Pattern Input
        input_layout = QHBoxLayout()
        
        lbl = QLabel("Pattern:")
        lbl.setStyleSheet("font-weight: bold;")
        input_layout.addWidget(lbl)
        
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setText(self.current_pattern)
        self.pattern_edit.setPlaceholderText("e.g. {Artist} - {Title}")
        self.pattern_edit.textChanged.connect(self._on_pattern_text_changed)
        input_layout.addWidget(self.pattern_edit)
        
        # Preset Buttons
        self.presets = [
            "{Artist} - {Title}",
            "{Artist} - {Album} - {Title}",
            "{Ignore} - {Artist} - {Title}", # Common: Track number
            "{Title}"
        ]
        
        preset_combo = QComboBox()
        preset_combo.addItems(["Load Preset..."] + self.presets)
        preset_combo.currentIndexChanged.connect(lambda idx: self._apply_preset(preset_combo, idx))
        input_layout.addWidget(preset_combo)
        
        layout.addLayout(input_layout)
        
        # 3. Preview Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Filename", "Artist", "Title", "Other Extracted"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # 4. Status / Error Message
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #FF5555;") # Red for errors
        layout.addWidget(self.status_lbl)
        
        # 5. Buttons
        btn_layout = QHBoxLayout()
        
        # Toggle: Dry Run
        self.check_test = QLabel(f"Processing {len(self.selected_songs)} items.")
        btn_layout.addWidget(self.check_test)
        
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setFixedSize(100, 36)
        btn_layout.addWidget(self.btn_cancel)
        
        self.btn_apply = GlowButton("APPLY TO ALL SELECTED")
        self.btn_apply.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_apply)
        
        layout.addLayout(btn_layout)
        
        # Debounce timer for parsing
        self.parse_timer = QTimer()
        self.parse_timer.setSingleShot(True)
        self.parse_timer.setInterval(300)
        self.parse_timer.timeout.connect(lambda: self._on_pattern_changed(self.pattern_edit.text()))

    def _apply_preset(self, combo, index):
        if index > 0:
            text = combo.currentText()
            self.pattern_edit.setText(text)
            combo.setCurrentIndex(0) # Reset to prompt

    def _on_pattern_text_changed(self, text):
        self.parse_timer.start()

    def _get_actual_filename(self, path):
        """Recover actual filename casing from disk (undoes DB normcase)."""
        if not path: return ""
        try:
            # pathlib.resolve() is the standard way to get true case on Windows
            from pathlib import Path
            return Path(path).resolve().name
        except Exception:
            return os.path.basename(path)

    def _on_pattern_changed(self, text):
        self.current_pattern = text
        self.parsed_results = {}
        self.status_lbl.setText("")
        
        compiled_re = PatternEngine.compile_extraction_regex(text)
        if not compiled_re:
            self.status_lbl.setText("Invalid Pattern Regex")
            self.table.setRowCount(0)
            return
            
        # Parse Preview Songs
        self.table.setRowCount(len(self.preview_songs))
        self.table.setSortingEnabled(False)
        
        match_count = 0
        
        for row, song in enumerate(self.preview_songs):
            if not song.path: continue
            
            # Use actual filename from disk to preserve Casing
            filename = self._get_actual_filename(song.path)
            name_only, ext = os.path.splitext(filename)
            
            data = PatternEngine.extract_metadata(name_only, compiled_re)
            # ... (rest of logic same as before, see context below or rewrite carefully)
            
            # Fill Columns
            file_item = QTableWidgetItem(filename)
            file_item.setToolTip(filename)
            self.table.setItem(row, 0, file_item)
            
            if data:
                # Store by Source ID (safe key)
                self.parsed_results[song.source_id] = data
                match_count += 1
                
                # Artist
                artist = data.get("performers", "")
                art_item = QTableWidgetItem(artist)
                if artist: art_item.setForeground(QColor(constants.COLOR_AMBER))
                self.table.setItem(row, 1, art_item)
                
                # Title
                title = data.get("title", "")
                tit_item = QTableWidgetItem(title)
                if title: tit_item.setForeground(QColor(constants.COLOR_AMBER))
                self.table.setItem(row, 2, tit_item)
                
                # Others
                others = []
                for k, v in data.items():
                    if k not in ["performers", "title"]:
                        others.append(f"{k}={v}")
                
                self.table.setItem(row, 3, QTableWidgetItem(", ".join(others)))
            else:
                # No match - Gray out
                for col in range(1, 4):
                    item = QTableWidgetItem("-")
                    item.setForeground(QColor("#555555"))
                    self.table.setItem(row, col, item)

        if match_count == 0:
            self.status_lbl.setText("No filenames matched the pattern.")
        else:
            self.status_lbl.setText(f"Examples: {match_count}/{len(self.preview_songs)} matched.")

    def get_parsed_data(self):
        """
        Returns full result set for ALL selected items.
        Re-runs regex on everything.
        """
        compiled_re = PatternEngine.compile_extraction_regex(self.current_pattern)
        if not compiled_re: return {}
        
        final_results = {}
        for song in self.selected_songs:
            if not song.path: continue
            
            # Use actual filename for final extraction too
            filename = self._get_actual_filename(song.path)
            name_only, _ = os.path.splitext(filename)
            
            data = PatternEngine.extract_metadata(name_only, compiled_re)
            
            if data:
                final_results[song.source_id] = data
        
        return final_results
