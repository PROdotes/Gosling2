from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableView, 
                             QAbstractItemView, QHeaderView, QFrame)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty
from PyQt6.QtGui import QStandardItemModel, QStandardItem


class HistoryDrawer(QFrame):
    """
    Left-side sliding drawer for the 'As Played' historical log.
    Uses QPropertyAnimation for smooth mission-control transitions.
    """
    def __init__(self, field_indices, parent=None):
        super().__init__(parent)
        self.field_indices = field_indices
        self.setObjectName("HistoryDrawer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title
        self.title = QLabel("AS PLAYED LOG", self)
        self.title.setObjectName("HistoryTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)

        # The Log Table (standard QTableView, styled via QSS)
        self.table_view = QTableView()
        self.table_view.setObjectName("HistoryTable")
        self.model = QStandardItemModel(0, 3)
        self.model.setHorizontalHeaderLabels(["TIME", "TITLE", "ARTIST"])
        self.table_view.setModel(self.model)
        
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setShowGrid(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setAlternatingRowColors(False)
        
        layout.addWidget(self.table_view)

        # Mock Data for Testing
        self._populate_mock_history()

    def _populate_mock_history(self):
        """Populate with dummy data for UI testing."""
        history = [
            ("20:15", "Bohemian Rhapsody", "Queen"),
            ("20:10", "Yesterday", "The Beatles"),
            ("20:05", "Another One Bites The Dust", "Queen"),
            ("20:00", "Summer Vibes", "Compilation"),
            ("19:55", "Hotel California", "Eagles"),
            ("19:50", "Stairway to Heaven", "Led Zeppelin"),
            ("19:45", "Imagine", "John Lennon"),
            ("19:40", "Sweet Child O' Mine", "Guns N' Roses"),
        ]
        for time_str, title, artist in history:
            items = [QStandardItem(time_str), QStandardItem(title), QStandardItem(artist)]
            self.model.appendRow(items)

    def add_entry(self, time_str: str, title: str, artist: str):
        """Add a new entry to the top of the log."""
        items = [QStandardItem(time_str), QStandardItem(title), QStandardItem(artist)]
        self.model.insertRow(0, items)

    # Property for Animation
    @pyqtProperty(int)
    def drawerWidth(self):
        return self.width()

    @drawerWidth.setter
    def drawerWidth(self, width):
        self.setFixedWidth(width)
