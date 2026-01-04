from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableView, QPushButton, QFrame, QFileDialog,
    QLineEdit, QComboBox, QHeaderView, QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QSortFilterProxyModel, QRegularExpression
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QFont, QColor
from ..widgets.glow_factory import GlowButton, GlowLineEdit, GlowComboBox
from pathlib import Path
import os
import re

class LogFilterProxyModel(QSortFilterProxyModel):
    """Custom proxy to filter by both Level and Search Text."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level_filter = "ALL LEVELS"
        self._search_regex = QRegularExpression()

    def setLevelFilter(self, level: str):
        self._level_filter = level
        self.invalidateFilter()

    def setSearchText(self, text: str):
        self._search_regex = QRegularExpression(re.escape(text), QRegularExpression.PatternOption.CaseInsensitiveOption)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        
        # 1. Level Filter (Column 1)
        if self._level_filter != "ALL LEVELS":
            level = model.index(source_row, 1, source_parent).data()
            if level != self._level_filter:
                return False
                
        # 2. Search Text Filter (Across Source and Message)
        if self._search_regex.isValid() and self._search_regex.pattern():
            source = model.index(source_row, 2, source_parent).data() or ""
            message = model.index(source_row, 3, source_parent).data() or ""
            if not (self._search_regex.match(source).hasMatch() or self._search_regex.match(message).hasMatch()):
                return False
                
        return True

class LogViewerDialog(QDialog):
    """
    Diagnostic Log Viewer (T-56 Diagnostic Deck).
    Parses and displays gosling.log in a filterable table.
    """
    
    LOG_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[([A-Z]+)\] \[([^\]]+)\] (.*)$')
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("DIAGNOSTIC CONSOLE")
        self.setMinimumSize(1000, 600)
        self.setObjectName("LogViewerDialog") 
        
        # Determine log path (Settings > Default)
        custom_path = self.settings_manager.get_log_path()
        if custom_path:
            self.log_path = Path(custom_path)
        else:
            # Replicate logger.py default logic
            self.log_path = Path(__file__).parent.parent.parent.parent / "gosling.log"
        
        self._last_size = 0
        
        # Models
        self.model = QStandardItemModel(0, 4)
        self.model.setHorizontalHeaderLabels(["TIMESTAMP", "LEVEL", "SOURCE", "MESSAGE"])
        
        self.proxy_model = LogFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        
        self._init_ui()
        
        # Setup Timer for auto-refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._auto_refresh)
        self.timer.start(2000) # Check every 2 seconds
        
        self.refresh_log()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # --- HEADER ---
        header_layout = QHBoxLayout()
        header = QLabel("SYSTEM DIAGNOSTICS")
        header.setObjectName("SidePanelHeader")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.lbl_path = QLabel(str(self.log_path))
        self.lbl_path.setObjectName("LogConsolePath")
        header_layout.addWidget(self.lbl_path)
        
        layout.addLayout(header_layout)

        # --- FILTER BAR (The Navigation Hub) ---
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(15)

        search_container = QHBoxLayout()
        lbl_search = QLabel("SEARCH")
        lbl_search.setObjectName("FieldLabel")
        lbl_search.setFixedWidth(60)
        self.txt_search = GlowLineEdit()
        self.txt_search.setPlaceholderText("Filter by source or message...")
        self.txt_search.textChanged.connect(self._on_filter_changed)
        search_container.addWidget(lbl_search)
        search_container.addWidget(self.txt_search)
        
        level_container = QHBoxLayout()
        lbl_level = QLabel("LEVEL")
        lbl_level.setObjectName("FieldLabel")
        lbl_level.setFixedWidth(50)
        self.cmb_level = GlowComboBox()
        self.cmb_level.addItems(["ALL LEVELS", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.cmb_level.currentIndexChanged.connect(self._on_filter_changed)
        self.cmb_level.setFixedWidth(140)
        level_container.addWidget(lbl_level)
        level_container.addWidget(self.cmb_level)

        filter_layout.addLayout(search_container, 1)
        filter_layout.addLayout(level_container)
        
        layout.addLayout(filter_layout)
        
        # --- TABLE VIEW ---
        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.setObjectName("LogTable") 
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        
        # Column logic
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        # Default Widths
        self.table.setColumnWidth(0, 180) # Timestamp
        self.table.setColumnWidth(1, 80)  # Level
        self.table.setColumnWidth(2, 120) # Source

        layout.addWidget(self.table)
        
        # --- CONTROL BAR ---
        btn_layout = QHBoxLayout()
        
        self.btn_refresh = GlowButton("FORCE REFRESH")
        self.btn_refresh.setFixedWidth(120)
        self.btn_refresh.clicked.connect(self.refresh_log)
        
        self.btn_open_folder = GlowButton("OPEN FOLDER")
        self.btn_open_folder.setFixedWidth(120)
        self.btn_open_folder.clicked.connect(self._on_open_folder)
        
        self.btn_clear = GlowButton("TRUNCATE LOG")
        self.btn_clear.setObjectName("ActionPill")
        self.btn_clear.setProperty("action_role", "secondary")
        self.btn_clear.setFixedWidth(180) # Increased further to prevent text clipping
        self.btn_clear.clicked.connect(self._on_clear_log)
        
        self.btn_close = GlowButton("CLOSE")
        self.btn_close.setFixedWidth(100)
        self.btn_close.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_open_folder)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)

    def refresh_log(self):
        """Read the log file and update the model."""
        if not self.log_path.exists():
            self.model.setRowCount(0)
            return
            
        try:
            # Get current size to track changes
            self._last_size = self.log_path.stat().st_size
            
            with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
                # Read last 250,000 characters for a healthy history
                f.seek(0, os.SEEK_END)
                size = f.tell()
                start_pos = max(0, size - 250000)
                f.seek(start_pos)
                
                content = f.read()
                lines = content.split('\n')
                
                # Parse lines into rows
                rows = []
                current_row = None
                
                for line in lines:
                    if not line.strip(): continue
                    
                    match = self.LOG_PATTERN.match(line)
                    if match:
                        timestamp, level, source, message = match.groups()
                        
                        items = [
                            QStandardItem(timestamp),
                            QStandardItem(level),
                            QStandardItem(source),
                            QStandardItem(message)
                        ]
                        
                        # Consolas for data
                        font = QFont("Consolas", 10)
                        for item in items:
                            item.setFont(font)
                        
                        # Level-based coloring
                        if level == "ERROR":
                            items[1].setForeground(QColor("#E53935")) 
                        elif level == "WARNING":
                            items[1].setForeground(QColor("#FFC66D")) 
                        elif level == "DEBUG":
                            items[1].setForeground(QColor("#666666")) 
                            
                        current_row = items
                        rows.append(items)
                    else:
                        if current_row:
                            msg_item = current_row[3]
                            msg_item.setText(msg_item.text() + "\n" + line)
                
                # Batch update
                self.model.setRowCount(0)
                for row in rows:
                    self.model.appendRow(row)
                
                # Auto-scroll if at bottom
                v_bar = self.table.verticalScrollBar()
                at_bottom = v_bar.value() >= v_bar.maximum() - 5
                if at_bottom or self.model.rowCount() < 100:
                    self.table.scrollToBottom()
                
        except Exception as e:
             from ...core import logger
             logger.error(f"UI Log Viewer failed to refresh: {e}")

    def _auto_refresh(self):
        """Periodically check if log file size changed."""
        if self.log_path.exists():
            try:
                current_size = self.log_path.stat().st_size
                if current_size != self._last_size:
                    self.refresh_log()
            except: pass

    def _on_filter_changed(self):
        """Update proxy model filters."""
        self.proxy_model.setLevelFilter(self.cmb_level.currentText())
        self.proxy_model.setSearchText(self.txt_search.text())

    def _on_open_folder(self):
        """Open the explorer containing the logs."""
        if os.name == 'nt':
            os.startfile(self.log_path.parent)
        else:
            import subprocess
            subprocess.run(['xdg-open', str(self.log_path.parent)])

    def _on_clear_log(self):
        """Truncate the log file with confirmation."""
        from PyQt6.QtWidgets import QMessageBox
        confirm = QMessageBox.question(
            self, 
            "Confirm Truncation", 
            "This will PERMANENTLY delete all current diagnostic logs. Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{timestamp} [INFO] [SYSTEM] --- LOG TRUNCATED BY USER ---\n")
            self.refresh_log()
        except: pass
