"""
Dialog for displaying import results and managing failed imports.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QListWidget, 
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QHeaderView,
    QWidget, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt
from ...resources import constants
import os


class ImportResultDialog(QDialog):
    def __init__(self, success_list: list, failure_list: list, import_service, parent=None):
        super().__init__(parent)
        self.success_list = success_list
        self.failure_list = failure_list
        self.import_service = import_service
        
        self.setWindowTitle("Import Results")
        self.resize(700, 500)
        self.setModal(True)
        
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Summary Header
        success_count = len(self.success_list)
        failure_count = len(self.failure_list)
        
        header = QLabel(f"Import Complete: {success_count} Imported, {failure_count} Failed")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
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

    def _init_success_tab(self):
        layout = QVBoxLayout(self.success_tab)
        list_widget = QListWidget()
        
        for item in self.success_list:
            path = item.get('path', '')
            name = os.path.basename(path)
            list_widget.addItem(f"{name} (ID: {item.get('id')})")
            
        layout.addWidget(list_widget)

    def _init_failure_tab(self):
        layout = QVBoxLayout(self.failure_tab)
        
        self.fail_table = QTableWidget()
        self.fail_table.setColumnCount(2)
        self.fail_table.setHorizontalHeaderLabels(["File", "Error Reason"])
        self.fail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.fail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.fail_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fail_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.fail_table.customContextMenuRequested.connect(self._show_context_menu)
        
        self._populate_fail_table()
        layout.addWidget(self.fail_table)
        
        # Action Bar for Failures
        actions = QHBoxLayout()
        
        del_all_btn = QPushButton("Delete All Failed Files")
        del_all_btn.setStyleSheet(f"background-color: {constants.COLOR_RED}; color: white;")
        del_all_btn.clicked.connect(self._delete_all_failed)
        actions.addWidget(del_all_btn)
        
        actions.addStretch()
        layout.addLayout(actions)

    def _populate_fail_table(self):
        self.fail_table.setRowCount(0)
        from PyQt6.QtGui import QColor, QBrush
        
        for i, item in enumerate(self.failure_list):
            path = item.get('path', '')
            error = item.get('error', 'Unknown Error')
            name = os.path.basename(path)
            
            self.fail_table.insertRow(i)
            
            is_already_imported = str(error).startswith("ALREADY_IMPORTED")
            
            name_item = QTableWidgetItem(name)
            name_item.setToolTip(path)
            name_item.setData(Qt.ItemDataRole.UserRole, path)
            self.fail_table.setItem(i, 0, name_item)
            
            err_item = QTableWidgetItem(error)
            err_item.setToolTip(error)
            # Store error in UserRole for context menu logic
            err_item.setData(Qt.ItemDataRole.UserRole, error)
            self.fail_table.setItem(i, 1, err_item)
            
            # Visual Feedback
            if is_already_imported:
                # Gray out to indicate "Safe / Do Not Touch"
                gray_brush = QBrush(QColor(constants.COLOR_GRAY))
                name_item.setForeground(gray_brush)
                err_item.setForeground(gray_brush)

    def _show_context_menu(self, pos):
        item = self.fail_table.itemAt(pos)
        if not item:
            return
            
        row = item.row()
        path_item = self.fail_table.item(row, 0)
        path = path_item.data(Qt.ItemDataRole.UserRole)
        
        # Get error from column 1
        err_item = self.fail_table.item(row, 1)
        error = err_item.data(Qt.ItemDataRole.UserRole)
        is_already_imported = str(error).startswith("ALREADY_IMPORTED")
        
        menu = QMenu(self)
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
