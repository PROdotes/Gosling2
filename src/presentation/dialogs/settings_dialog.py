from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QFrame, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt
from ..widgets.glow_factory import GlowButton, GlowLineEdit
import os

class SettingsDialog(QDialog):
    """
    Settings/Config Panel (T-52 MVP).
    Focused on library organization and renaming rules.
    """
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("OPERATIONS CONFIG")
        self.setMinimumWidth(500)
        self.setObjectName("AlbumManagerDialog") # Reuse standard dialog style
        
        # Frameless/Custom style support if needed, 
        # but standard dialog is fine if we style it in QSS.
        
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # --- HEADER ---
        header = QLabel("SYSTEM SETTINGS")
        header.setObjectName("SidePanelHeader") # Reuse side panel header style
        layout.addWidget(header)
        
        # --- SEPARATOR ---
        line = QFrame()
        line.setObjectName("FieldGroupLine") # Reuse shared separator
        layout.addWidget(line)
        
        # --- SECTION: LIBRARY ---
        lib_label = QLabel("LIBRARY ORGANIZATION")
        lib_label.setObjectName("FieldLabel") # Reuse field label style
        layout.addWidget(lib_label)
        
        # Root Directory Row
        root_layout = QHBoxLayout()
        self.txt_root_dir = GlowLineEdit()
        self.txt_root_dir.setPlaceholderText("Select root directory...")
        
        self.btn_browse = GlowButton("BROWSE")
        self.btn_browse.setFixedWidth(80)
        self.btn_browse.clicked.connect(self._on_browse_clicked)
        
        root_layout.addWidget(self.txt_root_dir, 1)
        root_layout.addWidget(self.btn_browse)
        layout.addLayout(root_layout)

        # Quality Row
        bitrate_layout = QHBoxLayout()
        bitrate_label = QLabel("MP3 QUALITY")
        bitrate_label.setFixedWidth(120)
        
        self.cmb_bitrate = QComboBox()
        self.cmb_bitrate.addItems([
            "VBR (V0)",
            "320k",
            "256k",
            "192k",
            "128k"
        ])
        self.cmb_bitrate.setObjectName("SidePanelCombo") # Reuse combo styling
        
        bitrate_layout.addWidget(bitrate_label)
        bitrate_layout.addWidget(self.cmb_bitrate, 1)
        layout.addLayout(bitrate_layout)

        # FFmpeg Path Row
        ffmpeg_label = QLabel("FFMPEG PATH")
        ffmpeg_label.setObjectName("FieldLabel")
        layout.addWidget(ffmpeg_label)

        ffmpeg_row = QHBoxLayout()
        self.txt_ffmpeg_path = GlowLineEdit()
        self.btn_ffmpeg_browse = GlowButton("PATH")
        self.btn_ffmpeg_browse.setFixedWidth(80)
        self.btn_ffmpeg_browse.clicked.connect(self._on_ffmpeg_browse_clicked)
        ffmpeg_row.addWidget(self.txt_ffmpeg_path, 1)
        ffmpeg_row.addWidget(self.btn_ffmpeg_browse)
        layout.addLayout(ffmpeg_row)
        
        # --- SECTION: WORKFLOW ---
        line2 = QFrame()
        line2.setObjectName("FieldGroupLine")
        layout.addWidget(line2)

        workflow_label = QLabel("WORKFLOW")
        workflow_label.setObjectName("FieldLabel")
        layout.addWidget(workflow_label)
        
        # Search Provider Row
        search_layout = QHBoxLayout()
        search_label = QLabel("SEARCH PROVIDER")
        search_label.setFixedWidth(120)
        
        self.cmb_search_provider = QComboBox()
        self.cmb_search_provider.addItems([
            "Google",
            "Spotify",
            "YouTube",
            "MusicBrainz",
            "Discogs"
        ])
        self.cmb_search_provider.setObjectName("SidePanelCombo")
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.cmb_search_provider, 1)
        layout.addLayout(search_layout)
        
        layout.addStretch()
        
        # --- BUTTONS ---
        button_row = QHBoxLayout()
        button_row.addStretch()
        
        self.btn_cancel = GlowButton("CANCEL")
        self.btn_cancel.setFixedWidth(100)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = GlowButton("APPLY")
        self.btn_save.setFixedWidth(100)
        self.btn_save.setObjectName("SaveAllButton") # Reuse save button flair
        self.btn_save.clicked.connect(self._on_save_clicked)
        
        button_row.addWidget(self.btn_cancel)
        button_row.addWidget(self.btn_save)
        layout.addLayout(button_row)

    def _load_settings(self):
        self.txt_root_dir.setText(self.settings_manager.get_root_directory())
        
        # Match bitrate to combo
        current_bitrate = self.settings_manager.get_conversion_bitrate()
        index = self.cmb_bitrate.findText(current_bitrate)
        if index >= 0:
            self.cmb_bitrate.setCurrentIndex(index)
        else:
            # Fallback for old custom values
            if "VBR" in current_bitrate.upper():
                self.cmb_bitrate.setCurrentIndex(0)
            else:
                self.cmb_bitrate.setCurrentText("320k")
                
        self.txt_ffmpeg_path.setText(self.settings_manager.get_ffmpeg_path())
        
        # Search Provider
        current_provider = self.settings_manager.get_search_provider()
        idx = self.cmb_search_provider.findText(current_provider)
        if idx >= 0:
            self.cmb_search_provider.setCurrentIndex(idx)

    def _on_browse_clicked(self):
        current = self.txt_root_dir.text() or "."
        path = QFileDialog.getExistingDirectory(self, "Select Root Directory", current)
        if path:
            self.txt_root_dir.setText(os.path.normpath(path))

    def _on_ffmpeg_browse_clicked(self):
        current = self.txt_ffmpeg_path.text() or "."
        path, _ = QFileDialog.getOpenFileName(self, "Select FFmpeg Executable", current, "Executables (*.exe);;All Files (*)")
        if path:
            self.txt_ffmpeg_path.setText(os.path.normpath(path))

    def _on_save_clicked(self):
        # Library
        root = self.txt_root_dir.text().strip()
        if root:
            # Normalize to handle trailing slashes or mixed separators
            normalized_root = os.path.normpath(root)
            self.settings_manager.set_root_directory(normalized_root)
            self.txt_root_dir.setText(normalized_root) # Update UI to show normalized path
            
        # Conversion
        self.settings_manager.set_conversion_bitrate(self.cmb_bitrate.currentText())
        self.settings_manager.set_ffmpeg_path(self.txt_ffmpeg_path.text().strip())
        
        # Search
        self.settings_manager.set_search_provider(self.cmb_search_provider.currentText())

        self.settings_manager.sync()
        self.accept()
