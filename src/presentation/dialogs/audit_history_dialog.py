"""
Audit History Dialog

A "Pro Console" flight recorder for database changes (The "Black Box").
Displays the ChangeLog table using a high-performance QTableView specific for Audit Data.
"""
from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableView, QHeaderView,
    QCheckBox, QComboBox, QMessageBox, QFrame, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, QAbstractTableModel, pyqtSlot
from PyQt6.QtGui import QColor, QBrush, QStandardItemModel, QStandardItem, QFont

from ..widgets.glow_factory import GlowLineEdit, GlowButton
from ...business.services.audit_service import AuditService
from ...core import logger

HISTORY_LIMIT = 500  # Load last N records by default

class AuditTableModel(QAbstractTableModel):
    """
    Read-only Table Model for Audit Logs.
    Optimized for display (colors, fonts).
    """
    
    COLUMNS = ["Time", "Type", "Table", "Field", "Record ID", "Old Value", "New Value", "Batch ID"]
    
    def __init__(self, data=None, resolver=None):
        super().__init__()
        self._data = data or []
        self._resolver = resolver

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.COLUMNS)

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.COLUMNS[section]
        return None

    def data(self, index, role):
        if not index.isValid():
            return None
            
        record = self._data[index.row()]
        col = index.column()
        
        # 0: Time, 1: Type (Inferred), 2: Table, 3: Field, 4: RecordID, 5: Old, 6: New
        
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return record.get('Time')
            if col == 1: 
                entry_type = record.get('EntryType')
                if entry_type == 'CHANGE':
                    # Infer CHANGE type
                    old = record.get('OldValue')
                    new = record.get('NewValue')
                    if old is None and new is not None: return "INSERT"
                    if old is not None and new is None: return "DELETE"
                    return "UPDATE"
                return entry_type # System Action (MERGE, IMPORT, etc)
                
            if col == 2: return record.get('TableName')
            if col == 3: return record.get('FieldName')
            if col == 4: 
                val = record.get('RecordID')
                if self._resolver and val:
                    name = self._resolver(record.get('TableName'), val)
                    if name: return f"{name} [#{val}]"
                return str(val or "")
            
            if col == 7: # Batch ID
                return record.get('BatchID') or ""

            if col in [5, 6]: 
                val = record.get('OldValue') if col == 5 else record.get('NewValue')
                if val is None: return "-"
                
                # Resolve IDs in values
                field_name = record.get('FieldName')
                if self._resolver and field_name and field_name.endswith('ID'):
                    target_table = None
                    if field_name == "ContributorID": target_table = "Contributors"
                    elif field_name == "AlbumID": target_table = "Albums"
                    elif field_name == "SourceID": target_table = "Songs"
                    elif field_name == "PublisherID": target_table = "Publishers"
                    
                    if target_table:
                        try:
                            res_name = self._resolver(target_table, int(val))
                            if res_name: return f"{res_name} [#{val}]"
                        except: pass
                
                # Special handling for ActionDetails (JSON)
                if record.get('EntryType') != 'CHANGE' and isinstance(val, str) and val.startswith('{'):
                    try:
                        import json
                        d = json.loads(val)
                        return ", ".join(f"{k}: {v}" for k, v in d.items())
                    except: pass

                return str(val)

        # Stylistic Tweaks
        if role == Qt.ItemDataRole.ForegroundRole:
            if col in [5, 6]: # Values
                return QColor("#E0E0E0") # Bright Text
            return QColor("#AAAAAA")     # Dim Metadata

        if role == Qt.ItemDataRole.FontRole:
            if col in [5, 6]: # Monospace for values
                f = QFont("Consolas", 10)
                return f

        # Row Coloring (Subtle Tinting for scanning)
        if role == Qt.ItemDataRole.BackgroundRole:
            entry_type = record.get('EntryType')
            if entry_type != 'CHANGE':
                # System actions (MERGE, PROMOTE etc) = Deep Blue
                return QColor(30, 45, 75) 
            
            old = record.get('OldValue')
            new = record.get('NewValue')
            
            if old is None and new is not None:
                return QColor(25, 55, 25)  # Green Tint (Insert)
            if old is not None and new is None:
                return QColor(70, 25, 25)  # Red Tint (Delete)
            if old is not None and new is not None:
                return QColor(75, 55, 25)  # Amber Tint (Update)


        return None
        
    def get_batch_id(self, row):
        """Helper to get batch ID for a specific row index."""
        if 0 <= row < len(self._data):
            return self._data[row].get('BatchID')
        return None


class AuditHistoryDialog(QDialog):
    
    def __init__(self, audit_service: AuditService, resolver=None, parent=None, initial_query=""):
        super().__init__(parent)
        self.audit_service = audit_service
        self.resolver = resolver
        self._initial_query = initial_query
        self.setWindowTitle("Data Flight Recorder")
        self.resize(1000, 600)
        self.setObjectName("AuditHistoryDialog")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # === HEADER ===
        header = QFrame()
        header.setObjectName("PanelHeader")
        header.setFixedHeight(50)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 12, 0)
        
        lbl_title = QLabel("DATA HISTORY")
        lbl_title.setObjectName("PanelTitle")
        h_layout.addWidget(lbl_title)
        
        h_layout.addStretch()
        
        self.btn_refresh = GlowButton("Refresh")
        self.btn_refresh.setFixedSize(80, 28)
        self.btn_refresh.clicked.connect(self._refresh_data)
        h_layout.addWidget(self.btn_refresh)
        
        layout.addWidget(header)
        
        # === FILTER BAR ===
        filter_bar = QFrame()
        filter_bar.setStyleSheet("background-color: #1A1A1A; border-bottom: 1px solid #333;")
        f_layout = QHBoxLayout(filter_bar)
        f_layout.setContentsMargins(8, 8, 8, 8)
        
        self.txt_search = GlowLineEdit()
        self.txt_search.setPlaceholderText("Filter by Record ID, Field Name, or Value...")
        if self._initial_query:
            self.txt_search.setText(self._initial_query)
        self.txt_search.textChanged.connect(self._on_filter_changed)
        f_layout.addWidget(self.txt_search)
        
        layout.addWidget(filter_bar)
        
        # === TABLE ===
        self.table_view = QTableView()
        self.table_view.setObjectName("AuditTable")
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setGridStyle(Qt.PenStyle.NoPen) # Cleaner look
        
        self.model = AuditTableModel(resolver=self.resolver)
        self.table_view.setModel(self.model)
        
        # Column Resizing
        h = self.table_view.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Time
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Type
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Table
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Field
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # ID
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)          # Old
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)          # New
        h.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)      # Batch ID
        
        # Hide Batch ID by default (Power User feature revealed via Context Menu or future update)
        self.table_view.setColumnHidden(7, True)
        
        # Context Menu
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)
        
        # Selection Handling (Batch Grouping)
        self.table_view.clicked.connect(self._on_row_clicked)
        
        layout.addWidget(self.table_view)
        
        # === FOOTER ===
        footer = QFrame()
        footer.setFixedHeight(30)
        footer.setStyleSheet("background-color: #121212; border-top: 1px solid #333;")
        foot_layout = QHBoxLayout(footer)
        foot_layout.setContentsMargins(10, 0, 10, 0)
        
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #666; font-family: Consolas;")
        foot_layout.addWidget(self.lbl_status)
        
        layout.addWidget(footer)
        
        # Load Data
        self._full_data = [] # Cache for filtering
        QTimer.singleShot(100, self._refresh_data)

    def _refresh_data(self):
        """Fetch latest logs from service."""
        try:
            raw_data = self.audit_service.get_unified_history(limit=HISTORY_LIMIT)
            self._full_data = raw_data
            self._apply_filter(self.txt_search.text())
            self.lbl_status.setText(f"Showing last {len(raw_data)} events (Changes & Actions).")
        except Exception as e:
            logger.error(f"Audit load error: {e}")
            self.lbl_status.setText("Error loading history.")

    def _on_filter_changed(self, text):
        self._apply_filter(text)

    def _apply_filter(self, query=""):
        query = query.lower().strip()
        if not query:
            self.model.update_data(self._full_data)
            return
            
        filtered = []
        for row in self._full_data:
            # SEARCH VALUES: Raw ID and Raw string values only (FASTER)
            # We don't resolve human names here because it hits the DB in a loop (slowness)
            search_corpus = f"{row.get('TableName')} {row.get('FieldName')} {row.get('RecordID')} {row.get('OldValue')} {row.get('NewValue')} {row.get('EntryType')}".lower()
            
            if query in search_corpus:
                filtered.append(row)
                
        self.model.update_data(filtered)

    def _on_row_clicked(self, index):
        """When a row is clicked, select all rows with the same BatchID."""
        if not index.isValid(): return
        
        batch_id = self.model.get_batch_id(index.row())
        if not batch_id: return
        
        # Select all rows with this batch ID
        selection = self.table_view.selectionModel()
        selection.clearSelection() # Clear previous
        
        # Determine strict matching mode
        # If user holds CTRL, maybe add? For now, simpler: Atomic Click = Atomic Batch Select
        
        from PyQt6.QtCore import QItemSelection, QItemSelectionRange
        
        # Scan model for matching rows (Linear scan ok for 500 items)
        # TODO: Optimize with a map if history grows
        rows_to_select = []
        for r in range(self.model.rowCount()):
            bid = self.model.get_batch_id(r)
            if bid == batch_id:
                # Add whole row
                # Range: (r, 0) to (r, COLS-1)
                idx_tl = self.model.index(r, 0)
                idx_br = self.model.index(r, self.model.columnCount()-1)
                selection.select(QItemSelectionRange(idx_tl, idx_br), QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)

    def _show_context_menu(self, pos):
        """Show context menu for table."""
        index = self.table_view.indexAt(pos)
        if not index.isValid(): return
        
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        menu = QMenu(self)
        
        batch_id = self.model.get_batch_id(index.row())
        
        # Copy Info
        action_copy_val = QAction("Copy Value", self)
        action_copy_val.triggered.connect(lambda: self._copy_to_clipboard(index.data()))
        menu.addAction(action_copy_val)
        
        if batch_id:
            menu.addSeparator()
            action_copy_batch = QAction(f"Copy Batch ID: {batch_id[:8]}...", self)
            action_copy_batch.triggered.connect(lambda: self._copy_to_clipboard(batch_id))
            menu.addAction(action_copy_batch)
            
            # Future: Undo Batch
            # action_undo = QAction("Undo This Batch (Experimental)", self)
            # action_undo.triggered.connect(lambda: self.audit_service.undo_batch(batch_id))
            # menu.addAction(action_undo)
            
        menu.exec(self.table_view.viewport().mapToGlobal(pos))
        
    def _copy_to_clipboard(self, text):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(str(text))
