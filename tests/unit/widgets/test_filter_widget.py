
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
        """Test that clicking 'Artists' emits reset_filter"""
        # Connect signal to mock
        mock_slot = MagicMock()
        widget.reset_filter.connect(mock_slot)
        
        # Manually create the "Artists" item as it would be in the tree
        # We need to find the index of the "Artists" item. 
        # Since we mocked populate with empty list, row 0 is "Artists"
        root_index = widget.tree_model.index(0, 0)
        item = widget.tree_model.itemFromIndex(root_index)
        assert item.text() == "Artists"
        
        # Simulate click
        widget._on_tree_clicked(root_index)
        
        mock_slot.assert_called_once()

    def test_filter_by_artist_signal(self, widget):
        """Test that clicking an artist emits filter_by_artist"""
        mock_slot = MagicMock()
        widget.filter_by_artist.connect(mock_slot)
        
        # Add a fake artist item
        from PyQt6.QtGui import QStandardItem
        artist_item = QStandardItem("Test Artist")
        artist_item.setData("Test Artist", Qt.ItemDataRole.UserRole)
        widget.tree_model.appendRow(artist_item)
        
        index = widget.tree_model.indexFromItem(artist_item)
        
        # Simulate click
        widget._on_tree_clicked(index)
        
        mock_slot.assert_called_with("Test Artist")

    def test_populate_empty_artist(self, widget):
        """Test population with empty artist name"""
        # Set mock to return mix of valid and empty
        widget.library_service.get_contributors_by_role.return_value = [
            (1, "Valid Artist"),
            (2, ""),
            (3, None)
        ]
        
        widget.populate()
        
        # Should have 1 actual artist group + root
        # Root is at row 0.
        root = widget.tree_model.item(0)
        assert root.text() == "Artists"
        
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
        assert v_group.child(0).text() == "Valid Artist"
