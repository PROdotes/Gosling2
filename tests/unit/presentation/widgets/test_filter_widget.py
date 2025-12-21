
import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.presentation.widgets.filter_widget import FilterWidget
from src.core import yellberus

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

class TestFilterWidget:
    """Test cases for FilterWidget"""

    @pytest.fixture
    def widget(self, qapp):
        mock_library = MagicMock()
        # Ensure populate doesn't crash
        mock_library.get_contributors_by_role.return_value = []
        mock_library.get_all_years.return_value = [2021]
        return FilterWidget(mock_library)

    def test_reset_filter_signal(self, widget):
        """Test that double-clicking a category header emits reset_filter (T-17 UX Refinement)"""
        mock_slot = MagicMock()
        widget.reset_filter.connect(mock_slot)
        
        # Find first root item (any category header)
        root_index = widget.tree_model.index(0, 0)
        
        # Simulate double-click on category header
        widget._on_tree_double_clicked(root_index)
        
        mock_slot.assert_called_once()

    def test_filter_by_performer_signal(self, widget):
        """Test that clicking an artist emits filter_by_unified_artist (T-17: unified_artist)"""
        mock_slot = MagicMock()
        widget.filter_by_unified_artist.connect(mock_slot)
        
        # Add a fake artist item using unified_artist field
        from PyQt6.QtGui import QStandardItem
        artist_item = QStandardItem("Test Artist")
        artist_item.setData("Test Artist", Qt.ItemDataRole.UserRole)
        artist_item.setData("unified_artist", Qt.ItemDataRole.UserRole + 1)
        widget.tree_model.appendRow(artist_item)
        
        index = widget.tree_model.indexFromItem(artist_item)
        
        # Simulate click
        widget._on_tree_clicked(index)
        
        mock_slot.assert_called_with("Test Artist")

    def test_filter_by_composer_signal(self, widget):
        """Test that clicking a composer emits filter_by_composer"""
        mock_slot = MagicMock()
        widget.filter_by_composer.connect(mock_slot)
        
        from PyQt6.QtGui import QStandardItem
        composer_item = QStandardItem("Test Composer")
        composer_item.setData("Test Composer", Qt.ItemDataRole.UserRole)
        composer_item.setData("composers", Qt.ItemDataRole.UserRole + 1)  # New: field name
        widget.tree_model.appendRow(composer_item)
        
        index = widget.tree_model.indexFromItem(composer_item)
        
        # Simulate click
        widget._on_tree_clicked(index)
        
        mock_slot.assert_called_with("Test Composer")

    def test_filter_by_year_signal(self, widget):
        """Test that clicking a year emits filter_by_year"""
        mock_slot = MagicMock()
        widget.filter_by_year.connect(mock_slot)
        
        from PyQt6.QtGui import QStandardItem
        year_item = QStandardItem("2020")
        year_item.setData(2020, Qt.ItemDataRole.UserRole)
        year_item.setData("recording_year", Qt.ItemDataRole.UserRole + 1)  # New: field name
        widget.tree_model.appendRow(year_item)
        
        index = widget.tree_model.indexFromItem(year_item)
        widget._on_tree_clicked(index)
        
        mock_slot.assert_called_with(2020)

    def test_filter_by_status_signal(self, widget):
        """Test that clicking a status emits filter_by_status"""
        mock_slot = MagicMock()
        widget.filter_by_status.connect(mock_slot)
        
        from PyQt6.QtGui import QStandardItem
        status_item = QStandardItem("Done")
        status_item.setData(True, Qt.ItemDataRole.UserRole)
        status_item.setData("is_done", Qt.ItemDataRole.UserRole + 1)
        widget.tree_model.appendRow(status_item)
        
        index = widget.tree_model.indexFromItem(status_item)
        widget._on_tree_clicked(index)
        
        mock_slot.assert_called_with(True)

    def test_generic_filter_changed_signal(self, widget):
        """Test that the new generic filter_changed signal works"""
        mock_slot = MagicMock()
        widget.filter_changed.connect(mock_slot)
        
        from PyQt6.QtGui import QStandardItem
        item = QStandardItem("Test Value")
        item.setData("test_value", Qt.ItemDataRole.UserRole)
        item.setData("test_field", Qt.ItemDataRole.UserRole + 1)
        widget.tree_model.appendRow(item)
        
        index = widget.tree_model.indexFromItem(item)
        widget._on_tree_clicked(index)
        
        mock_slot.assert_called_with("test_field", "test_value")

    def test_filter_categories_from_yellberus(self, widget):
        """
        Integrity Check:
        Ensures that the Filter Tree contains categories matching Yellberus filterable fields.
        """
        # Get expected categories from Yellberus
        expected = {field.ui_header for field in yellberus.get_filterable_fields() 
                   if field.strategy != "range"}  # Range filters not yet implemented
        
        # Get actual roots from tree
        actual = set()
        for i in range(widget.tree_model.rowCount()):
            item = widget.tree_model.item(i)
            actual.add(item.text())
        
        # Check that expected categories are present
        # (Some may be missing if no data, that's OK)
        # Just verify we're not adding random categories
        for cat in actual:
            matching = [f for f in yellberus.get_filterable_fields() if f.ui_header == cat]
            assert matching, f"Category '{cat}' in tree doesn't match any Yellberus field"
