from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QPushButton, QDialogButtonBox, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class MetadataViewerDialog(QDialog):
    """Dialog to compare File metadata vs Library metadata"""
    
    def __init__(self, file_song, db_song, raw_tags=None, parent=None):
        super().__init__(parent)
        self.file_song = file_song
        self.db_song = db_song
        self.raw_tags = raw_tags or {}
        self.setWindowTitle("Metadata Comparison")
        self.resize(800, 600)
        self._init_ui()
        self._populate_table()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header info
        file_name = self.file_song.path.split("\\")[-1] if self.file_song.path else "Unknown"
        layout.addWidget(QLabel(f"<b>File:</b> {file_name}"))
        layout.addWidget(QLabel(f"<b>Path:</b> {self.file_song.path}"))

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Field", "File (Source)", "Library (Database)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_table(self):
        # Common ID3v2.3/v2.4 frames
        ID3_FRAMES = {}
        try:
            import json
            import os
            # Resolve path: src/presentation/widgets/../../resources/id3_frames.json
            # Current file: src/presentation/widgets/metadata_viewer_dialog.py
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up two levels to src
            src_dir = os.path.dirname(os.path.dirname(base_dir))
            json_path = os.path.join(src_dir, 'resources', 'id3_frames.json')
            
            with open(json_path, 'r', encoding='utf-8') as f:
                ID3_FRAMES = json.load(f)
        except Exception as e:
            print(f"Failed to load ID3 frames JSON: {e}")
            # Fallback basics if file missing
            ID3_FRAMES = {
                "TIT2": "Title",
                "TPE1": "Artist",
                "TALB": "Album"
            }

        # 1. Mapped Fields
        mapped_fields = [
            ("Title", "title", ["TIT2"]),
            ("Performer(s)", "performers", ["TPE1"]),
            ("Composer(s)", "composers", ["TCOM"]),
            ("Album Artist", "album_artists", ["TPE2"]),
            ("Producer(s)", "producers", ["TIPL", "TMCL", "TXXX:PRODUCER"]), # Approximate mapping
            ("Duration", "formatted_duration", ["TLEN"]), 
            ("BPM", "bpm", ["TBPM"]),
        ]

        # Tracking used raw keys to avoid duplication
        used_id3_keys = set()
        for _, _, keys in mapped_fields:
            used_id3_keys.update(keys)

        self.table.setRowCount(0)

        # -- Section: Core Metadata --
        self._add_section_header("Core Metadata")
        
        for label, attr, _ in mapped_fields:
            file_val = getattr(self.file_song, attr, None)
            db_val = getattr(self.db_song, attr, None) if self.db_song else None
            
            self._add_row(label, file_val, db_val)

        # -- Section: Raw / Extended Metadata --
        self._add_section_header("Extended / Raw ID3 Tags")
        
        sorted_keys = sorted(self.raw_tags.keys())
        for key in sorted_keys:
            if key in used_id3_keys:
                continue
            
            # Use description if available
            # Check for colon in key (e.g. TXXX:PRODUCER)
            base_key = key.split(':')[0]
            desc = ID3_FRAMES.get(base_key, "")
            
            if desc:
                label = f"{key} - {desc}"
            else:
                label = key
                
            val = self.raw_tags[key]
            self._add_row(label, val, None, is_raw=True)

    def _add_section_header(self, title):
        row = self.table.rowCount()
        self.table.insertRow(row)
        header_item = QTableWidgetItem(title)
        
        # Enhanced Styling for Headers
        # Dark Blue-Grey background for distinction
        header_item.setBackground(QColor(40, 50, 60)) 
        header_item.setForeground(QColor(220, 230, 240)) # Off-white/blueish
        header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter) # Center text
        
        header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        font = header_item.font()
        font.setBold(True)
        # font.setPointSize(font.pointSize() + 1) # Slightly larger?
        header_item.setFont(font)
        
        self.table.setItem(row, 0, header_item)
        self.table.setSpan(row, 0, 1, 3)
        
        # Increase row height for header
        self.table.setRowHeight(row, 30)

    def _add_row(self, label, file_val, db_val, is_raw=False):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 1. Label
        self.table.setItem(row, 0, QTableWidgetItem(label))

        # 2. Values
        file_str = self._format_value(file_val)
        if is_raw:
             # Raw tags are not in DB by definition (unless mapped, which we skipped)
             db_str = "Not Stored"
        else:
             db_str = self._format_value(db_val) if self.db_song or (db_val is not None) else "NOT IN DB"

        file_item = QTableWidgetItem(file_str)
        db_item = QTableWidgetItem(db_str)

        if is_raw:
            # Grey out the DB column to indicate it's expected to be missing
            db_item.setForeground(QColor("gray"))
            italic = db_item.font()
            italic.setItalic(True)
            db_item.setFont(italic)
        else:
            # Comparison logic for Core Data
            # If db is missing entirely (song not in lib), grey out
            if not self.db_song and db_val is None:
                 db_item.setForeground(QColor("gray"))
            elif file_str != db_str:
                # Discrepancy!
                bg_color = QColor(255, 220, 220) # Light red/pink
                file_item.setBackground(bg_color)
                db_item.setBackground(bg_color)
                self.table.item(row, 0).setBackground(bg_color) # Highlight label too

                font = file_item.font()
                font.setBold(True)
                file_item.setFont(font)
                db_item.setFont(font)

        self.table.setItem(row, 1, file_item)
        self.table.setItem(row, 2, db_item)

    def _format_value(self, val):
        if val is None:
            return ""
        if isinstance(val, list):
            return ", ".join(sorted(val))
        return str(val)
