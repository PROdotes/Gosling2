
import pytest
from PyQt6.QtWidgets import QDialog, QTableView, QLineEdit, QPushButton
from PyQt6.QtCore import Qt, QTimer
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.presentation.dialogs.audit_history_dialog import AuditHistoryDialog, AuditTableModel

@pytest.fixture
def mock_service():
    """Mock AuditService."""
    service = MagicMock()
    # Mock data return
    service.get_recent_changes.return_value = [
        {
            'LogTimestamp': '2023-01-01 10:00:00',
            'LogTableName': 'Songs',
            'LogFieldName': 'Title',
            'RecordID': 123,
            'OldValue': 'Old Title',
            'NewValue': 'New Title',
            'BatchID': 'batch-guid-1'
        },
        {
            'LogTimestamp': '2023-01-01 10:05:00',
            'LogTableName': 'Songs',
            'LogFieldName': None, 
            'RecordID': 124,
            'OldValue': None,
            'NewValue': 'Some Insert Data',
            'BatchID': 'batch-guid-2'
        },
        {
            'LogTimestamp': '2023-01-01 10:10:00',
            'LogTableName': 'Songs',
            'LogFieldName': None,
            'RecordID': 125,
            'OldValue': 'Delete Me',
            'NewValue': None,
            'BatchID': 'batch-guid-3'
        }
    ]
    return service

@pytest.fixture
def dialog(qtbot, mock_service):
    """Fixture for AuditHistoryDialog."""
    dlg = AuditHistoryDialog(mock_service)
    qtbot.addWidget(dlg)
    return dlg

def test_initialization(dialog, mock_service):
    """Test standard initialization."""
    assert dialog.windowTitle() == "Data Flight Recorder"
    assert isinstance(dialog.table_view, QTableView)
    assert isinstance(dialog.model, AuditTableModel)
    
    # Check if data loaded (QTimer might need wait)
    # We can manually trigger _refresh_data since it's singleShot(100)
    dialog._refresh_data()
    
    mock_service.get_recent_changes.assert_called()
    assert dialog.model.rowCount() == 3

def test_filtering(dialog):
    """Test filtering logic."""
    dialog._refresh_data()
    
    # 1. Filter by "Title" (Field Name)
    dialog._apply_filter("Title")
    # Should match row 1
    assert dialog.model.rowCount() == 1
    assert dialog.model._data[0]['LogFieldName'] == 'Title'
    
    # 2. Filter by "Delete" (Value)
    dialog._apply_filter("Delete")
    assert dialog.model.rowCount() == 1
    assert dialog.model._data[0]['RecordID'] == 125
    
    # 3. Clear Filter
    dialog._apply_filter("")
    assert dialog.model.rowCount() == 3

def test_view_logic(dialog):
    """Test Model's view logic (Type inference)."""
    dialog._refresh_data()
    model = dialog.model
    # Row 0: Update
    idx_type = model.index(0, 1) # Type col
    assert model.data(idx_type, Qt.ItemDataRole.DisplayRole) == "UPDATE"
    
    # Row 1: Insert (Old None, New !None)
    idx_type_ins = model.index(1, 1)
    assert model.data(idx_type_ins, Qt.ItemDataRole.DisplayRole) == "INSERT"
    
    # Row 2: Delete (Old !None, New None)
    idx_type_del = model.index(2, 1)
    assert model.data(idx_type_del, Qt.ItemDataRole.DisplayRole) == "DELETE"

def test_refresh_button(qtbot, dialog, mock_service):
    """Test refresh button triggers service call."""
    mock_service.get_recent_changes.reset_mock()
    
    with qtbot.waitSignal(dialog.btn_refresh.clicked, timeout=1000, raising=False):
        qtbot.mouseClick(dialog.btn_refresh, Qt.MouseButton.LeftButton)
        
    mock_service.get_recent_changes.assert_called()
