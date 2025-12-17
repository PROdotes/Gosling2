import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMenu, QTableView, QMessageBox
from PyQt6.QtGui import QAction, QStandardItem
from PyQt6.QtCore import Qt, QPoint

from src.presentation.widgets.library_widget import LibraryWidget
from src.business.services.library_service import LibraryService
from src.business.services.metadata_service import MetadataService
from src.business.services.settings_manager import SettingsManager

class TestLibraryContextMenu:
    @pytest.fixture
    def widget(self, qtbot):
        library_service = MagicMock(spec=LibraryService)
        metadata_service = MagicMock(spec=MetadataService)
        settings_manager = MagicMock(spec=SettingsManager)
        
        # Mock initial load
        library_service.get_all_songs.return_value = ([], [])
        
        widget = LibraryWidget(library_service, metadata_service, settings_manager)
        qtbot.addWidget(widget)
        widget.show() # Ensure widget is visible/exposed for selection model to work reliably
        
        # Patch QMessageBox methods globally for this widget fixture
        with patch('PyQt6.QtWidgets.QMessageBox.information'), \
             patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warn, \
             patch('PyQt6.QtWidgets.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            widget.mock_warn = mock_warn # Attach to widget for access in tests
            yield widget

    def setup_selection_mock(self, widget, status_list):
        """Helper to setup table with items having specific IsDone status"""
        widget.library_model.clear()
        
        for i, is_done in enumerate(status_list):
            items = []
            for col in range(10):
                text = f"Item {col}"
                if col == 0: # ID
                    text = str(i+100)
                
                item = QStandardItem(text)
                # Important: Set UserRole for validation logic
                item.setData(text, Qt.ItemDataRole.UserRole)
                items.append(item)
            
            # Setup IsDone (col 9) - Override CheckState
            items[9].setCheckable(True)
            check_state = Qt.CheckState.Checked if is_done else Qt.CheckState.Unchecked
            items[9].setCheckState(check_state)
            # Ensure IsDone UserRole matches boolean for completeness check if needed
            items[9].setData(is_done, Qt.ItemDataRole.UserRole)
            
            widget.library_model.appendRow(items)
            
            # Ensure selection model has the model (Paranoid fix for QtWarning)
            if not widget.table_view.selectionModel().model():
                widget.table_view.selectionModel().setModel(widget.proxy_model)
            
            # Allow event loop to process model updates
            from PyQt6.QtCore import QCoreApplication
            QCoreApplication.processEvents()
                
            index = widget.proxy_model.mapFromSource(widget.library_model.index(i, 0))
            if not index.isValid():
                raise RuntimeError("Proxy index invalid - mapping failed")
                
            widget.table_view.selectionModel().select(index, widget.table_view.selectionModel().SelectionFlag.Select | widget.table_view.selectionModel().SelectionFlag.Rows)
            
        # Verify selection took effect
        if len(widget.table_view.selectionModel().selectedRows()) != len(status_list):
             # Force select directly on source if proxy fails? No, that breaks logic.
             print(f"DEBUG: Selection failed. Expected {len(status_list)}, got {len(widget.table_view.selectionModel().selectedRows())}")

    def test_context_menu_all_done(self, widget):
        """Test: All items done -> Option "Mark as Not Done" """
        self.setup_selection_mock(widget, [True, True])
        
        with patch('PyQt6.QtWidgets.QMenu.exec') as mock_exec, \
             patch('PyQt6.QtWidgets.QMenu.addAction') as mock_add:
             
            # Capture added actions
            actions = []
            mock_add.side_effect = lambda a: actions.append(a)
            
            widget._show_table_context_menu(QPoint(0,0))
            
            # Verify we found the status action
            status_action = None
            for action in actions:
                if action and "Mark as" in action.text():
                    status_action = action
                    break
            
            assert status_action is not None
            assert status_action.text() == "Mark as Not Done"
            assert status_action.isEnabled() is True
            
            # Verify trigger calls service
            widget.library_service.update_song_status.return_value = True
            status_action.trigger()
            
            # Should call update_song_status(id, False) twice
            assert widget.library_service.update_song_status.call_count == 2
            widget.library_service.update_song_status.assert_any_call(100, False) # item 0 id
            widget.library_service.update_song_status.assert_any_call(101, False) # item 1 id

    def test_context_menu_all_not_done(self, widget):
        """Test: All items not done -> Option "Mark as Done" """
        self.setup_selection_mock(widget, [False, False])
        
        with patch('PyQt6.QtWidgets.QMenu.exec'), \
             patch('PyQt6.QtWidgets.QMenu.addAction') as mock_add:
             
            actions = []
            mock_add.side_effect = lambda a: actions.append(a)
            
            widget._show_table_context_menu(QPoint(0,0))
            
            status_action = next((a for a in actions if a and "Mark as" in a.text()), None)
            
            assert status_action is not None
            assert status_action.text() == "Mark as Done"
            assert status_action.isEnabled() is True
            
            widget.library_service.update_song_status.return_value = True
            status_action.trigger()
            
            # Should call update_song_status(id, True)
            widget.library_service.update_song_status.assert_any_call(100, True)

    def test_context_menu_mixed_status(self, widget):
        """Test: Mixed status -> Option "Mixed Status" (Disabled) """
        self.setup_selection_mock(widget, [True, False])
        
        with patch('PyQt6.QtWidgets.QMenu.exec'), \
             patch('PyQt6.QtWidgets.QMenu.addAction') as mock_add:
             
            actions = []
            mock_add.side_effect = lambda a: actions.append(a)
            
            widget._show_table_context_menu(QPoint(0,0))
            
            status_action = next((a for a in actions if a and "Mixed Status" in a.text()), None)
            
            assert status_action is not None
            
            assert status_action is not None
            assert status_action.text() == "Mixed Status (Cannot Toggle)"
            assert status_action.isEnabled() is False

    # @pytest.mark.skip(reason="Cannot suppress QMessageBox popup in test environment reliably")
    def test_context_menu_validate_incomplete(self, widget):
        """Test: Marking as done blocked if fields incomplete"""
        self.setup_selection_mock(widget, [False])
        
        # Mock criteria
        widget.completeness_criteria = {'title': {'required': True}}
        
        # Explicit patch to mirror drag_drop test success pattern
        with patch('PyQt6.QtWidgets.QMessageBox.warning') as local_mock_warn:
            # Replace item 0,2 with explicitly empty/none item
            bad_item = QStandardItem("")
            bad_item.setData(None, Qt.ItemDataRole.UserRole)
            widget.library_model.setItem(0, widget.COL_TITLE, bad_item)
            
            # Verify Model State
            check_item = widget.library_model.item(0, widget.COL_TITLE)
            assert check_item.text() == ""
            assert check_item.data(Qt.ItemDataRole.UserRole) is None
            
            # Verify Selection State (Critical Debug)
            selected = widget.table_view.selectionModel().selectedRows()
            if not selected:
                # Force re-select if lost
                index = widget.proxy_model.mapFromSource(widget.library_model.index(0, 0))
                widget.table_view.selectionModel().select(index, widget.table_view.selectionModel().SelectionFlag.Select | widget.table_view.selectionModel().SelectionFlag.Rows)
                selected = widget.table_view.selectionModel().selectedRows()
            
            assert len(selected) > 0, "Selection lost before toggle!"
            
            # Execute
            widget._toggle_status(True)
             
            # Verify check was called
            # We access the LOCAL mock
            assert local_mock_warn.called, "Warning not called! Validation logic failed or skipped."
            assert "Validation Failed" in local_mock_warn.call_args[0][1]
            
            # Verify service NOT called
            widget.library_service.update_song_status.assert_not_called()
