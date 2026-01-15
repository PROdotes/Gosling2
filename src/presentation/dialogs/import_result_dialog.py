"""
Dialog for displaying import results and managing failed imports.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QWidget, QMessageBox, QMenu, QFrame, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QBrush, QFont
from ...resources import constants
import os


# Error Category System
ERROR_CATEGORIES = {
    'DUPLICATE': {'color': constants.COLOR_GRAY, 'icon': '⊘', 'label': 'Duplicate', 'keywords': ['ALREADY_IMPORTED']},
    'ACCESS': {'color': constants.COLOR_RED, 'icon': '🔒', 'label': 'Access', 'keywords': ['Permission denied', 'Access denied', 'permission']},
    'MISSING': {'color': constants.COLOR_CYAN, 'icon': '?', 'label': 'Missing', 'keywords': ['Not found', 'File not found', 'not exist']},
    'FORMAT': {'color': constants.COLOR_MAGENTA, 'icon': '⚠', 'label': 'Format', 'keywords': ['Invalid format', 'Unsupported', 'corrupt', 'invalid']},
    'UNKNOWN': {'color': constants.COLOR_RED, 'icon': '!', 'label': 'Unknown', 'keywords': []}
}


def categorize_error(error_message: str) -> str:
    """Categorize error message into error type."""
    error_lower = str(error_message).lower()

    for category_key, category_info in ERROR_CATEGORIES.items():
        for keyword in category_info['keywords']:
            if keyword.lower() in error_lower:
                return category_key

    return 'UNKNOWN'


class ImportResultDialog(QDialog):
    def __init__(self, success_list: list, failure_list: list, import_service, parent=None):
        super().__init__(parent)
        self.success_list = success_list
        self.failure_list = failure_list
        self.import_service = import_service
        self.current_filter = 'ALL'  # For error filtering

        self.setWindowTitle("Import Results")
        self.resize(800, 600)
        self.setModal(True)
        self.setObjectName("ImportResultDialog")

        # Apply theme styling
        self.setStyleSheet(f"""
            QDialog#ImportResultDialog {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2A2A2A,
                    stop:0.02 #222222,
                    stop:1 #080808);
                color: #AAAAAA;
                font-family: "Bahnschrift Condensed", "Segoe UI", sans-serif;
            }}
        """)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        success_count = len(self.success_list)
        failure_count = len(self.failure_list)

        # Enhanced Header Bar
        header = QFrame()
        header.setObjectName("DialogHeader")
        header.setStyleSheet(f"""
            QFrame#DialogHeader {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2A2A2A,
                    stop:0.02 #222222,
                    stop:1 #080808);
                border: 1px solid #333333;
                border-radius: 8px;
                border-bottom: 2px solid #1A1A1A;
            }}
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)

        # Title
        lbl_title = QLabel("IMPORT RESULTS")
        lbl_title.setObjectName("DialogTitleLarge")
        lbl_title.setStyleSheet(f"""
            QLabel#DialogTitleLarge {{
                color: {constants.COLOR_AMBER};
                font-size: 16pt;
                font-weight: bold;
                background: transparent;
            }}
        """)
        header_layout.addWidget(lbl_title)

        # Subtitle with summary
        lbl_hint = QLabel(f"{success_count} IMPORTED  |  {failure_count} FAILED")
        lbl_hint.setObjectName("DialogHint")
        lbl_hint.setStyleSheet("""
            QLabel#DialogHint {{
                color: #888888;
                font-size: 10pt;
                background: transparent;
            }}
        """)
        header_layout.addWidget(lbl_hint)

        layout.addWidget(header)

        # Success Celebration (only if successes > 0)
        if success_count > 0:
            celebration = self._create_celebration_widget(success_count)
            layout.addWidget(celebration)
        
        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Success Tab
        self.success_tab = QWidget()
        self._init_success_tab()
        self.tabs.addTab(self.success_tab, f"Succeeded ({success_count})")
        
        # Failure Tab
        self.failure_tab = QWidget()
        self._init_failure_tab()
        self.tabs.addTab(self.failure_tab, f"Failed ({failure_count})")
        
        # Show Failure tab first if there are failures
        if failure_count > 0:
            self.tabs.setCurrentWidget(self.failure_tab)
            
        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedSize(100, 30)
        footer.addWidget(close_btn)
        
        layout.addLayout(footer)

    def _create_celebration_widget(self, count: int) -> QFrame:
        """Create success celebration widget with animation."""
        celebration_frame = QFrame()
        celebration_frame.setObjectName("CelebrationFrame")
        celebration_frame.setStyleSheet(f"""
            QFrame#CelebrationFrame {{
                background-color: #111111;
                border: 1px solid {constants.COLOR_AMBER};
                border-radius: 6px;
                margin: 10px;
                padding: 15px;
            }}
        """)

        celebration_layout = QHBoxLayout(celebration_frame)

        # Large checkmark icon
        icon_label = QLabel("✓")
        icon_label.setStyleSheet(f"""
            QLabel {{
                color: {constants.COLOR_AMBER};
                font-size: 48pt;
                font-weight: bold;
                background: transparent;
            }}
        """)
        celebration_layout.addWidget(icon_label)

        # Text section
        text_layout = QVBoxLayout()

        status_label = QLabel("INTAKE COMPLETE")
        status_label.setStyleSheet(f"""
            QLabel {{
                color: {constants.COLOR_AMBER};
                font-size: 18pt;
                font-weight: bold;
                background: transparent;
            }}
        """)
        text_layout.addWidget(status_label)

        count_label = QLabel(f"{count} FILES SECURED")
        count_label.setStyleSheet(f"""
            QLabel {{
                color: {constants.COLOR_MUTED_AMBER};
                font-size: 12pt;
                background: transparent;
            }}
        """)
        text_layout.addWidget(count_label)

        celebration_layout.addLayout(text_layout)
        celebration_layout.addStretch()

        # Add fade-in animation
        opacity_effect = QGraphicsOpacityEffect(celebration_frame)
        celebration_frame.setGraphicsEffect(opacity_effect)

        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(800)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start()

        # Store animation reference to prevent garbage collection
        celebration_frame.animation = animation

        return celebration_frame

    def _init_success_tab(self):
        layout = QVBoxLayout(self.success_tab)
        layout.setContentsMargins(10, 10, 10, 10)

        list_widget = QListWidget()
        list_widget.setObjectName("SuccessListWidget")
        list_widget.setStyleSheet(f"""
            QListWidget#SuccessListWidget {{
                background-color: #111111;
                border: 1px solid #333333;
                color: #AAAAAA;
                font-size: 10pt;
                outline: none;
            }}
            QListWidget#SuccessListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid #1A1A1A;
            }}
            QListWidget#SuccessListWidget::item:hover {{
                background-color: #1A1A1A;
            }}
        """)

        for item in self.success_list:
            path = item.get('path', '')
            name = os.path.basename(path)
            item_id = item.get('id')
            # Format: filename in default color, ID in gray
            list_item = QListWidgetItem(f"{name}  (ID: {item_id})")
            list_item.setToolTip(path)
            list_widget.addItem(list_item)

        layout.addWidget(list_widget)

    def _init_failure_tab(self):
        layout = QVBoxLayout(self.failure_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Filter buttons
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(5)

        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("color: #888888; font-size: 10pt;")
        filter_layout.addWidget(filter_label)

        # Create filter buttons
        self.filter_buttons = {}
        filter_options = ['ALL', 'DUPLICATE', 'ACCESS', 'MISSING', 'FORMAT', 'UNKNOWN']

        for filter_key in filter_options:
            btn = QPushButton(ERROR_CATEGORIES.get(filter_key, {}).get('label', filter_key).upper() if filter_key != 'ALL' else 'ALL')
            btn.setObjectName(f"FilterButton_{filter_key}")
            btn.setFixedHeight(28)
            btn.setCheckable(True)
            btn.setChecked(filter_key == 'ALL')
            btn.clicked.connect(lambda checked, key=filter_key: self._apply_filter(key))

            # Button styling
            if filter_key == 'ALL':
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #1A1A1A;
                        color: #AAAAAA;
                        border: 1px solid #333333;
                        border-radius: 4px;
                        padding: 4px 12px;
                    }}
                    QPushButton:checked {{
                        background-color: {constants.COLOR_AMBER};
                        color: #000000;
                        border: 1px solid {constants.COLOR_AMBER};
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        border: 1px solid #555555;
                    }}
                """)
            else:
                category_color = ERROR_CATEGORIES[filter_key]['color']
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #1A1A1A;
                        color: #AAAAAA;
                        border: 1px solid #333333;
                        border-radius: 4px;
                        padding: 4px 12px;
                    }}
                    QPushButton:checked {{
                        background-color: {category_color};
                        color: #000000;
                        border: 1px solid {category_color};
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        border: 1px solid #555555;
                    }}
                """)

            self.filter_buttons[filter_key] = btn
            filter_layout.addWidget(btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Failure table with 3 columns: Type, File, Error Reason
        self.fail_table = QTableWidget()
        self.fail_table.setColumnCount(3)
        self.fail_table.setHorizontalHeaderLabels(["Type", "File", "Error Reason"])
        self.fail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.fail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.fail_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.fail_table.setColumnWidth(0, 120)
        self.fail_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fail_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.fail_table.customContextMenuRequested.connect(self._show_context_menu)
        self.fail_table.setAlternatingRowColors(True)

        # Table styling
        self.fail_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: #111111;
                border: 1px solid #333333;
                color: #AAAAAA;
                gridline-color: #1A1A1A;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 8px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: #2A2A2A;
            }}
            QHeaderView::section {{
                background-color: #1A1A1A;
                color: {constants.COLOR_AMBER};
                padding: 6px;
                border: none;
                border-bottom: 2px solid #333333;
                font-weight: bold;
            }}
            QTableWidget::item:alternate {{
                background-color: #0D0D0D;
            }}
        """)

        self._populate_fail_table()
        layout.addWidget(self.fail_table)

        # Action Bar for Failures
        actions = QHBoxLayout()

        del_all_btn = QPushButton("Delete All Failed Files")
        del_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {constants.COLOR_RED};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #FF6666;
            }}
            QPushButton:pressed {{
                background-color: #CC0000;
            }}
        """)
        del_all_btn.clicked.connect(self._delete_all_failed)
        actions.addWidget(del_all_btn)

        actions.addStretch()
        layout.addLayout(actions)

    def _populate_fail_table(self):
        self.fail_table.setRowCount(0)

        # Filter failure list based on current filter
        filtered_list = self.failure_list
        if self.current_filter != 'ALL':
            filtered_list = [
                item for item in self.failure_list
                if categorize_error(item.get('error', '')) == self.current_filter
            ]

        for i, item in enumerate(filtered_list):
            path = item.get('path', '')
            error = item.get('error', 'Unknown Error')
            name = os.path.basename(path)

            # Categorize error
            category_key = categorize_error(error)
            category_info = ERROR_CATEGORIES[category_key]
            category_color = category_info['color']
            category_icon = category_info['icon']
            category_label = category_info['label']

            self.fail_table.insertRow(i)

            is_already_imported = str(error).startswith("ALREADY_IMPORTED")

            # Column 0: Type (icon + label)
            type_text = f"{category_icon}  {category_label}"
            type_item = QTableWidgetItem(type_text)
            type_item.setToolTip(f"{category_label} Error")
            type_item.setForeground(QBrush(QColor(category_color)))
            type_item.setFont(QFont("Bahnschrift Condensed", 10, QFont.Weight.Bold))
            type_item.setData(Qt.ItemDataRole.UserRole, category_key)
            self.fail_table.setItem(i, 0, type_item)

            # Column 1: File name
            name_item = QTableWidgetItem(name)
            name_item.setToolTip(path)
            name_item.setData(Qt.ItemDataRole.UserRole, path)
            self.fail_table.setItem(i, 1, name_item)

            # Column 2: Error Reason
            err_item = QTableWidgetItem(error)
            err_item.setToolTip(error)
            err_item.setData(Qt.ItemDataRole.UserRole, error)
            self.fail_table.setItem(i, 2, err_item)

            # Visual Feedback: Add left border accent by setting row color
            # Gray out protected items
            if is_already_imported:
                gray_brush = QBrush(QColor(constants.COLOR_GRAY))
                type_item.setForeground(gray_brush)
                name_item.setForeground(gray_brush)
                err_item.setForeground(gray_brush)
            else:
                # Subtle color tint for non-protected items
                name_item.setForeground(QBrush(QColor("#AAAAAA")))

    def _apply_filter(self, filter_key: str):
        """Apply error category filter to the table."""
        # Uncheck all buttons except the selected one
        for key, btn in self.filter_buttons.items():
            btn.setChecked(key == filter_key)

        self.current_filter = filter_key
        self._populate_fail_table()

    def _show_context_menu(self, pos):
        item = self.fail_table.itemAt(pos)
        if not item:
            return

        row = item.row()
        # Get path from column 1 (File column)
        path_item = self.fail_table.item(row, 1)
        path = path_item.data(Qt.ItemDataRole.UserRole)

        # Get error from column 2 (Error Reason column)
        err_item = self.fail_table.item(row, 2)
        error = err_item.data(Qt.ItemDataRole.UserRole)
        is_already_imported = str(error).startswith("ALREADY_IMPORTED")

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: #1A1A1A;
                color: #AAAAAA;
                border: 1px solid #333333;
            }}
            QMenu::item:selected {{
                background-color: {constants.COLOR_AMBER};
                color: #000000;
            }}
            QMenu::item:disabled {{
                color: #555555;
            }}
        """)

        del_action = menu.addAction("Delete File")

        if is_already_imported:
            del_action.setEnabled(False)
            del_action.setText("Delete File (Protected Master Copy)")

        action = menu.exec(self.fail_table.mapToGlobal(pos))

        if action == del_action:
            self._delete_file(path, row)

    def _delete_file(self, path, row):
        confirm = QMessageBox.question(
            self, 
            "Confirm Deletion", 
            f"Are you sure you want to permanently delete:\n{path}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            if self.import_service.delete_file(path):
                # Remove from list and table
                self.fail_table.removeRow(row)
                # Determine which index in failure_list matches (assumes order is preserved)
                # To be safe, filter by path
                self.failure_list = [x for x in self.failure_list if x.get('path') != path]
                self._update_tab_title()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete file. Check permissions or if it's open.")

    def _delete_all_failed(self):
        if not self.failure_list:
            return
            
        # Filter purely deletable files (exclude ALREADY_IMPORTED)
        deletable_list = [
            item for item in self.failure_list 
            if not str(item.get('error', '')).startswith("ALREADY_IMPORTED")
        ]
        
        if not deletable_list:
            QMessageBox.information(
                self, 
                "Nothing to Delete", 
                "All failed items are safe master copies already in the library.\nAction cancelled to prevent data loss."
            )
            return

        confirm = QMessageBox.question(
            self, 
            "Confirm Mass Deletion", 
            f"This will permanently delete {len(deletable_list)} redundant files.\nSafe master copies will satisfy 'ALREADY_IMPORTED' errors and be skipped.\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            failed_deletions = []
            # We must reconstruct the failure list to include the skipped ones + failed deletions
            remaining_failures = [
                item for item in self.failure_list 
                if str(item.get('error', '')).startswith("ALREADY_IMPORTED")
            ]
            
            for item in deletable_list:
                path = item.get('path')
                if not self.import_service.delete_file(path):
                    failed_deletions.append(path)
                    remaining_failures.append(item)
            
            self.failure_list = remaining_failures
            self._populate_fail_table()
            self._update_tab_title()
            
            if failed_deletions:
                QMessageBox.warning(self, "Partial Success", f"Could not delete {len(failed_deletions)} files.")

    def _update_tab_title(self):
        count = len(self.failure_list)
        self.tabs.setTabText(1, f"Failed ({count})")
        # Also update the header subtitle
        success_count = len(self.success_list)
        # Find the DialogHint label and update it
        for child in self.findChildren(QLabel):
            if child.objectName() == "DialogHint":
                child.setText(f"{success_count} IMPORTED  |  {count} FAILED")
                break
