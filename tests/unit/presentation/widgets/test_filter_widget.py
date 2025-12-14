
import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.presentation.widgets.filter_widget import FilterWidget

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
        return FilterWidget(mock_library)

    def test_reset_filter_signal(self, widget):
        """Test that clicking 'Performers' emits reset_filter"""
        # Connect signal to mock
        mock_slot = MagicMock()
        widget.reset_filter.connect(mock_slot)
        
        # Manually create the "Performers" item as it would be in the tree
        # With empty mock, populate() creates 2 roots: Performers(0), Composers(1)
        root_index = widget.tree_model.index(0, 0)
        item = widget.tree_model.itemFromIndex(root_index)
        assert item.text() == "Performers"
        
        # Simulate click
        widget._on_tree_clicked(root_index)
        
        mock_slot.assert_called_once()

    def test_filter_by_performer_signal(self, widget):
        """Test that clicking a performer emits filter_by_performer"""
        mock_slot = MagicMock()
        widget.filter_by_performer.connect(mock_slot)
        
        # Add a fake performer item
        from PyQt6.QtGui import QStandardItem
        performer_item = QStandardItem("Test Performer")
        performer_item.setData("Test Performer", Qt.ItemDataRole.UserRole)
        performer_item.setData("Performer", Qt.ItemDataRole.UserRole + 1) # Set Role
        widget.tree_model.appendRow(performer_item)
        
        index = widget.tree_model.indexFromItem(performer_item)
        
        # Simulate click
        widget._on_tree_clicked(index)
        
        mock_slot.assert_called_with("Test Performer")

    def test_filter_by_composer_signal(self, widget):
        """Test that clicking a composer emits filter_by_composer"""
        mock_slot = MagicMock()
        widget.filter_by_composer.connect(mock_slot)
        
        # Add a fake composer item
        from PyQt6.QtGui import QStandardItem
        composer_item = QStandardItem("Test Composer")
        composer_item.setData("Test Composer", Qt.ItemDataRole.UserRole)
        composer_item.setData("Composer", Qt.ItemDataRole.UserRole + 1) # Set Role
        widget.tree_model.appendRow(composer_item)
        
        index = widget.tree_model.indexFromItem(composer_item)
        
        # Simulate click
        widget._on_tree_clicked(index)
        
        mock_slot.assert_called_with("Test Composer")

    def test_populate_empty_performer(self, widget):
        """Test population with empty performer name"""
        # Set mock to return mix of valid and empty
        def side_effect(role):
            if role == "Performer":
                return [(1, "Valid Performer"), (2, ""), (3, None)]
            return []
        
        widget.library_service.get_contributors_by_role.side_effect = side_effect
        
        widget.populate()
        
        # Should have 1 actual performer group + root
        # Root is at row 0 (Populated sequentially, Performer first)
        root = widget.tree_model.item(0)
        assert root.text() == "Performers"
        
        # Valid Artist starts with V.
        # Check that we don't have items for empty strings
        # The logic:
        # 1. Finds all first chars -> "V"
        # 2. Creates letter nodes -> "V"
        # 3. Iterates list:
        #    - "Valid Artist" -> adds to V
        #    - "" -> continue
        #    - None -> continue
        
        assert root.rowCount() == 1 # Only "V" group
        v_group = root.child(0)
        assert v_group.text() == "V"
        assert v_group.rowCount() == 1
        assert v_group.child(0).text() == "Valid Performer"
