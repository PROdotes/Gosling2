from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QPushButton, QDialogButtonBox, QLabel, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

class MetadataViewerDialog(QDialog):
    """Dialog to compare File metadata vs Library metadata"""
    
    # Signals
    import_requested = pyqtSignal()
    export_requested = pyqtSignal()

    def __init__(self, file_song, db_song, raw_tags=None, parent=None):
        super().__init__(parent)
        self.file_song = file_song
        self.db_song = db_song
        self.raw_tags = raw_tags or {}
        
        # State tracking
        self.has_discrepancies = False
        self.file_has_newer = False
        self.db_has_newer = False # Conceptual, really just different
        
        self.setWindowTitle("Metadata Comparison")
        self.resize(800, 600)
        self._init_ui()
        self._populate_table()
        self._update_button_state()

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
        button_layout = QHBoxLayout()
        
        self.btn_import = QPushButton("Import to Database (File -> DB)")
        self.btn_import.setToolTip("Update the library database with values from the MP3 file tags.")
        self.btn_import.clicked.connect(self._on_import_clicked)
        
        self.btn_export = QPushButton("Export to File (DB -> File)")
        self.btn_export.setToolTip("Update the MP3 file tags with values from the library database.")
        self.btn_export.clicked.connect(self._on_export_clicked)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        
        button_layout.addWidget(self.btn_import)
        button_layout.addWidget(self.btn_export)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)

    def _update_button_state(self):
        # Enable import if there are ANY discrepancies (assuming File is truth usually)
        # OR if DB entry is missing completely
        missing_db = self.db_song is None
        
        self.btn_import.setEnabled(missing_db or self.has_discrepancies)
        
        # Enable export only if DB exists AND there are discrepancies
        # Note: Writing logic checks will happen in the signal handler or upstream
        self.btn_export.setEnabled(not missing_db and self.has_discrepancies)

    def _on_import_clicked(self):
        # Emit signal to let parent handle the actual repository update
        self.import_requested.emit()
        self.accept()

    def _on_export_clicked(self):
        # Emit signal to let parent handle file writing
        self.export_requested.emit()
        self.accept()

    def _populate_table(self):
        # Reset state
        self.has_discrepancies = False
        
        # Common ID3v2.3/v2.4 frames
        ID3_FRAMES = {}
        try:
            import json
            import os
            # Resolve path: src/resources/id3_frames.json
            base_dir = os.path.dirname(os.path.abspath(__file__))
            src_dir = os.path.dirname(os.path.dirname(base_dir))
            json_path = os.path.join(src_dir, 'resources', 'id3_frames.json')
            
            with open(json_path, 'r', encoding='utf-8') as f:
                ID3_FRAMES = json.load(f)
        except Exception as e:
            print(f"Failed to load ID3 frames JSON: {e}")
            pass
            
        self.ID3_FRAMES = ID3_FRAMES
        from src.core import yellberus

        # 1. Mapped Fields (Using Yellberus Registry)
        self.mapped_fields = []
        used_id3_keys = set()
        
        # Reverse lookup for ID3 frames from JSON
        field_to_frames = {}
        for frame_code, frame_info in ID3_FRAMES.items():
            if isinstance(frame_info, dict) and 'field' in frame_info:
                f_name = frame_info['field']
                if f_name not in field_to_frames:
                    field_to_frames[f_name] = []
                field_to_frames[f_name].append(frame_code)

        for field in yellberus.FIELDS:
            # Show portable fields + duration
            if not field.portable and field.name != "duration":
                continue
            
            attr = field.model_attr or field.name
            if attr == "name": attr = "title"  # Property alias
            if attr == "duration": attr = "formatted_duration" # Property alias
            
            frames = field_to_frames.get(field.name, [])
            self.mapped_fields.append((field.ui_header, attr, frames))
            used_id3_keys.update(frames)

        # Ensure legacy/dual keys are tracked as used
        used_id3_keys.update(["TKEY", "TYER", "TIPL", "TEXT"])

        self.table.setRowCount(0)
        
        # -- Section: Core Metadata --
        self._add_section_header("Core Metadata")
        
        for label, attr, _ in self.mapped_fields:
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
            base_key = key.split(':')[0]
            frame_info = ID3_FRAMES.get(base_key, "")
            
            # Handle both old (string) and new (object) formats
            if isinstance(frame_info, dict):
                desc = frame_info.get("description", "")
            else:
                desc = frame_info
            
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
        header_item.setBackground(QColor(40, 50, 60)) 
        header_item.setForeground(QColor(220, 230, 240))
        header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        font = header_item.font()
        font.setBold(True)
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
                self.has_discrepancies = True
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
