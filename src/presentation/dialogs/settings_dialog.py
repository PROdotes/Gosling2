from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QFrame, QCheckBox, QComboBox, QSpinBox, QMessageBox,
    QTabWidget, QWidget, QScrollArea
)
from PyQt6.QtCore import Qt
from ..widgets.glow_factory import GlowButton, GlowLineEdit, GlowToggle
import os

class SettingsDialog(QDialog):
    """
    Settings/Config Panel (T-52 MVP).
    Focused on library organization and renaming rules.
    """
    
    def __init__(self, settings_manager, renaming_service, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.renaming_service = renaming_service
        
        self.setWindowTitle("OPERATIONS CONFIG")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setObjectName("AlbumManagerDialog") # Reuse standard dialog style
        
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # --- TAB WIDGET (Styled via theme.qss) ---
        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")
        
        # Tab 1: General (Existing Settings)
        self.tab_general = QWidget()
        self.tab_general.setObjectName("GeneralTabContent")
        self._init_general_tab()
        self.tabs.addTab(self.tab_general, "General")
        
        # Tab 2: Renaming Rules (New)
        from ..widgets.renaming_rules_widget import RenamingRulesWidget
        self.tab_rules = RenamingRulesWidget(self.renaming_service)
        self.tab_rules.setObjectName("RulesTabContent")
        self.tabs.addTab(self.tab_rules, "Renaming Rules")
        
        main_layout.addWidget(self.tabs)
        
        # --- BOTTOM BAR (Common) ---
        bottom_frame = QFrame()
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(20, 10, 20, 10)
        
        self.btn_cancel = GlowButton("CANCEL")
        self.btn_cancel.setFixedWidth(100)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = GlowButton("APPLY")
        self.btn_save.setFixedWidth(100)
        self.btn_save.setObjectName("SaveAllButton")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._on_save_clicked)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_cancel)
        bottom_layout.addWidget(self.btn_save)
        
        main_layout.addWidget(bottom_frame)

    def _init_general_tab(self):
        layout = QVBoxLayout(self.tab_general)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # --- HEADER ---
        header = QLabel("SYSTEM CONFIGURATION")
        header.setObjectName("SidePanelHeader")
        layout.addWidget(header)
        
        # --- SEPARATOR ---
        line = QFrame()
        line.setObjectName("FieldGroupLine")
        layout.addWidget(line)
        
        # --- 1. LIBRARY ORGANIZATION ---
        lib_label = QLabel("LIBRARY ORGANIZATION")
        lib_label.setObjectName("FieldLabel")
        layout.addWidget(lib_label)
        
        # Root Directory Row
        root_layout = QHBoxLayout()
        self.txt_root_dir = GlowLineEdit()
        self.txt_root_dir.setPlaceholderText("Select root directory...")
        
        self.btn_browse = GlowButton("BROWSE")
        self.btn_browse.setAutoDefault(False)
        self.btn_browse.setFixedWidth(80)
        self.btn_browse.clicked.connect(self._on_browse_clicked)
        
        root_layout.addWidget(self.txt_root_dir, 1)
        root_layout.addWidget(self.btn_browse)
        layout.addLayout(root_layout)

        # Database Path Row (Advanced)
        db_layout = QHBoxLayout()
        self.txt_db_path = GlowLineEdit()
        self.txt_db_path.setPlaceholderText("Default (.gosling2.db)")
        self.txt_db_path.setToolTip("Custom location for the library database. Requires restart.")
        
        self.btn_db_browse = GlowButton("DB PATH")
        self.btn_db_browse.setAutoDefault(False)
        self.btn_db_browse.setFixedWidth(80)
        self.btn_db_browse.clicked.connect(self._on_db_browse_clicked)
        
        db_layout.addWidget(self.txt_db_path, 1)
        db_layout.addWidget(self.btn_db_browse)
        layout.addLayout(db_layout)

        # Log Path Row (Advanced)
        log_layout = QHBoxLayout()
        self.txt_log_path = GlowLineEdit()
        self.txt_log_path.setPlaceholderText("Default (gosling.log)")
        self.txt_log_path.setToolTip("Path to the diagnostic log file. Requires restart.")
        
        self.btn_log_browse = GlowButton("LOG PATH")
        self.btn_log_browse.setAutoDefault(False)
        self.btn_log_browse.setFixedWidth(80)
        self.btn_log_browse.clicked.connect(self._on_log_browse_clicked)
        
        log_layout.addWidget(self.txt_log_path, 1)
        log_layout.addWidget(self.btn_log_browse)
        layout.addLayout(log_layout)

        # --- 2. FILE MANAGEMENT ---
        line_ren = QFrame()
        line_ren.setObjectName("FieldGroupLine")
        layout.addWidget(line_ren)

        ren_label = QLabel("FILE MANAGEMENT")
        ren_label.setObjectName("FieldLabel")
        layout.addWidget(ren_label)

        # Toggles Group
        self.chk_rename_enabled = GlowToggle()
        self.chk_rename_enabled.set_labels("ON", "OFF")
        layout.addLayout(self._add_toggle_row("ENABLE AUTO-RENAMING", self.chk_rename_enabled))

        self.chk_write_tags = GlowToggle()
        self.chk_write_tags.set_labels("ON", "OFF")
        layout.addLayout(self._add_toggle_row("WRITE TO TAGS", self.chk_write_tags, "If disabled, metadata changes will only be saved to the database."))

        self.chk_delete_zip = GlowToggle()
        self.chk_delete_zip.set_labels("ON", "OFF")
        layout.addLayout(self._add_toggle_row("DELETE ZIP AFTER IMPORT", self.chk_delete_zip, "Delete ZIP files after successful import."))
        
        # Note: Pattern Input removed from here - it's handled via Rules Tab now

        # --- 3. TRANSCODING ---
        line_trans = QFrame()
        line_trans.setObjectName("FieldGroupLine")
        layout.addWidget(line_trans)
        
        trans_label = QLabel("TRANSCODING")
        trans_label.setObjectName("FieldLabel")
        layout.addWidget(trans_label)

        # Conversion Toggles
        self.chk_conversion_enabled = GlowToggle()
        self.chk_conversion_enabled.set_labels("ON", "OFF")
        layout.addLayout(self._add_toggle_row("ENABLE TRANSCODING", self.chk_conversion_enabled))
        
        self.chk_delete_wav = GlowToggle()
        self.chk_delete_wav.set_labels("ON", "OFF")
        layout.addLayout(self._add_toggle_row("DELETE WAV AFTER CONVERSION", self.chk_delete_wav, "Delete original WAV after successful conversion."))

        # Quality Row
        bitrate_layout = QHBoxLayout()
        bitrate_label = QLabel("MP3 QUALITY")
        bitrate_label.setFixedWidth(120)
        
        self.cmb_bitrate = QComboBox()
        self.cmb_bitrate.addItems(["VBR (V0)", "320k", "256k", "192k", "128k"])
        self.cmb_bitrate.setObjectName("SidePanelCombo")
        
        bitrate_layout.addWidget(bitrate_label)
        bitrate_layout.addWidget(self.cmb_bitrate, 1)
        layout.addLayout(bitrate_layout)

        # FFmpeg Path Row
        ffmpeg_row = QHBoxLayout()
        ffmpeg_label = QLabel("FFMPEG PATH")
        ffmpeg_label.setFixedWidth(120)
        
        self.txt_ffmpeg_path = GlowLineEdit()
        self.btn_ffmpeg_browse = GlowButton("PATH")
        self.btn_ffmpeg_browse.setAutoDefault(False)
        self.btn_ffmpeg_browse.setFixedWidth(80)
        self.btn_ffmpeg_browse.clicked.connect(self._on_ffmpeg_browse_clicked)
        
        ffmpeg_row.addWidget(ffmpeg_label)
        ffmpeg_row.addWidget(self.txt_ffmpeg_path, 1)
        ffmpeg_row.addWidget(self.btn_ffmpeg_browse)
        layout.addLayout(ffmpeg_row)

        # --- 4. METADATA ---
        line_meta = QFrame()
        line_meta.setObjectName("FieldGroupLine")
        layout.addWidget(line_meta)

        meta_label = QLabel("METADATA SOURCES")
        meta_label.setObjectName("FieldLabel")
        layout.addWidget(meta_label)
        
        # Search Provider Row
        search_layout = QHBoxLayout()
        search_label = QLabel("SEARCH PROVIDER")
        search_label.setFixedWidth(120)
        
        self.cmb_search_provider = QComboBox()
        self.cmb_search_provider.addItems(["Google", "Spotify", "YouTube", "MusicBrainz", "Discogs"])
        self.cmb_search_provider.setObjectName("SidePanelCombo")
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.cmb_search_provider, 1)
        layout.addLayout(search_layout)

        # Default Album Type Row
        album_type_layout = QHBoxLayout()
        album_type_label = QLabel("DEFAULT ALBUM TYPE")
        album_type_label.setFixedWidth(160)
        album_type_label.setObjectName("FieldLabel")
        
        self.cmb_default_album_type = QComboBox()
        self.cmb_default_album_type.addItems(["Album", "Single", "EP", "Compilation"])
        self.cmb_default_album_type.setObjectName("SidePanelCombo")
        
        album_type_layout.addWidget(album_type_label)
        album_type_layout.addWidget(self.cmb_default_album_type, 1)
        layout.addLayout(album_type_layout)

        # Default Year Row
        year_layout = QHBoxLayout()

        # Checkbox for Default Year
        self.chk_default_year = QCheckBox("DEFAULT YEAR")
        self.chk_default_year.setFixedWidth(160)
        self.chk_default_year.setObjectName("FieldLabel")
        self.chk_default_year.toggled.connect(self._on_year_toggled)
        
        from ...core import yellberus
        fdef = yellberus.get_field('recording_year')
        min_year_val = fdef.min_value if fdef and fdef.min_value is not None else 1860
        max_year_val = fdef.max_value if fdef and fdef.max_value is not None else 9999

        self.spin_default_year = QSpinBox()
        self.spin_default_year.setRange(int(min_year_val), int(max_year_val)) 
        self.spin_default_year.setFixedHeight(30)
        self.spin_default_year.setObjectName("SettingsSpin")
        self.spin_default_year.setEnabled(False) 
        
        year_layout.addWidget(self.chk_default_year)
        year_layout.addWidget(self.spin_default_year, 1)
        layout.addLayout(year_layout)
        
        layout.addStretch()

    def _add_toggle_row(self, label_text, toggle_obj, tooltip=""):
        """Helper to create a standard left-aligned toggle row."""
        row = QHBoxLayout()
        row.setSpacing(10)
        
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        if tooltip:
            label.setToolTip(tooltip)
            toggle_obj.setToolTip(tooltip)
            
        row.addWidget(toggle_obj)
        row.addWidget(label, 1)
        return row

    def _load_settings(self):
        # General Load
        self.txt_root_dir.setText(self.settings_manager.get_root_directory())
        self.txt_db_path.setText(self.settings_manager.get_database_path() or "")
        self.txt_log_path.setText(self.settings_manager.get_log_path() or "")
        
        self.chk_rename_enabled.setChecked(self.settings_manager.get_rename_enabled())
        self.chk_delete_zip.setChecked(self.settings_manager.get_delete_zip_after_import())
        self.chk_write_tags.setChecked(self.settings_manager.get_write_tags())
        
        self.chk_conversion_enabled.setChecked(self.settings_manager.get_conversion_enabled())
        self.chk_delete_wav.setChecked(self.settings_manager.get_delete_wav_after_conversion())

        current_bitrate = self.settings_manager.get_conversion_bitrate()
        index = self.cmb_bitrate.findText(current_bitrate)
        if index >= 0: self.cmb_bitrate.setCurrentIndex(index)
        
        self.txt_ffmpeg_path.setText(self.settings_manager.get_ffmpeg_path())
        
        current_provider = self.settings_manager.get_search_provider()
        idx = self.cmb_search_provider.findText(current_provider)
        if idx >= 0: self.cmb_search_provider.setCurrentIndex(idx)

        current_album_type = self.settings_manager.get_default_album_type()
        a_idx = self.cmb_default_album_type.findText(current_album_type)
        if a_idx >= 0: self.cmb_default_album_type.setCurrentIndex(a_idx)

        val = self.settings_manager.get_default_year()
        if val > 0:
            self.chk_default_year.setChecked(True)
            self.spin_default_year.setValue(val)
            self.spin_default_year.setEnabled(True)
        else:
            self.chk_default_year.setChecked(False)
            self.spin_default_year.setValue(2000)
            self.spin_default_year.setEnabled(False)

    def _on_year_toggled(self, checked):
        self.spin_default_year.setEnabled(checked)

    def _on_browse_clicked(self):
        current = self.txt_root_dir.text() or "."
        path = QFileDialog.getExistingDirectory(self, "Select Root Directory", current)
        if path: self.txt_root_dir.setText(os.path.normpath(path))

    def _on_ffmpeg_browse_clicked(self):
        current = self.txt_ffmpeg_path.text() or "."
        path, _ = QFileDialog.getOpenFileName(self, "Select FFmpeg Executable", current, "Executables (*.exe);;All Files (*)")
        if path: self.txt_ffmpeg_path.setText(os.path.normpath(path))

    def _on_db_browse_clicked(self):
        current = self.txt_db_path.text() or "."
        path, _ = QFileDialog.getOpenFileName(self, "Select Database Location", current, "SQLite Database (*.db);;All Files (*)")
        if path: self.txt_db_path.setText(os.path.normpath(path))

    def _on_log_browse_clicked(self):
        current = self.txt_log_path.text() or "."
        path, _ = QFileDialog.getOpenFileName(self, "Select Log Location", current, "Log Files (*.log);;All Files (*)")
        if path: self.txt_log_path.setText(os.path.normpath(path))
            
    def _on_save_clicked(self):
        # 1. Save General Settings
        if self.chk_default_year.isChecked():
            from ...core import yellberus
            fdef = next((f for f in yellberus.FIELDS if f.name == 'recording_year'), None)
            if fdef and self.spin_default_year.value() < fdef.min_value:
                 QMessageBox.warning(self, "Invalid configuration", f"Default Year must be at least {fdef.min_value}.")
                 return

        root = self.txt_root_dir.text().strip()
        if root:
            self.settings_manager.set_root_directory(os.path.normpath(root))
            
        db_path = self.txt_db_path.text().strip()
        if db_path and db_path != self.settings_manager.get_database_path():
             QMessageBox.information(self, "Restart Required", "Database path changed. Restart required.")
             self.settings_manager.set_database_path(db_path)
             
        log_path = self.txt_log_path.text().strip()
        if log_path and log_path != self.settings_manager.get_log_path():
             QMessageBox.information(self, "Restart Required", "Log path changed. Restart required.")
             self.settings_manager.set_log_path(log_path)

        self.settings_manager.set_rename_enabled(self.chk_rename_enabled.isChecked())
        self.settings_manager.set_delete_zip_after_import(self.chk_delete_zip.isChecked())
        self.settings_manager.set_write_tags(self.chk_write_tags.isChecked())

        self.settings_manager.set_conversion_enabled(self.chk_conversion_enabled.isChecked())
        self.settings_manager.set_delete_wav_after_conversion(self.chk_delete_wav.isChecked())
        self.settings_manager.set_conversion_bitrate(self.cmb_bitrate.currentText())
        self.settings_manager.set_ffmpeg_path(self.txt_ffmpeg_path.text().strip())
        
        self.settings_manager.set_search_provider(self.cmb_search_provider.currentText())
        self.settings_manager.set_default_album_type(self.cmb_default_album_type.currentText())
        
        if self.chk_default_year.isChecked():
            self.settings_manager.set_default_year(self.spin_default_year.value())
        else:
            self.settings_manager.set_default_year(0)

        self.settings_manager.sync()
        
        # 2. Save Rules
        self.tab_rules.save_changes()
        
        self.accept()
