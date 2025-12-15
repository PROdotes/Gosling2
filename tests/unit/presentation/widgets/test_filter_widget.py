
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
        mock_library.get_all_years.return_value = [2021]
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

    def test_filter_categories_integrity(self, widget):
        """
        Integrity Check:
        Ensures that the Filter Tree contains all expected top-level categories.
        If a new field like 'RecordingYear' or 'Genre' is added to the system,
        it MUST be exposed in the Filter Tree.
        """
        # We expect these categories to be present in the tree roots
        expected_categories = {
            "Performers",
            "Composers",
            "Lyricists",
            "Producers",
            "Years" # New field!
        }
        
        # 1. Get actual roots
        actual_categories = set()
        for i in range(widget.tree_model.rowCount()):
            item = widget.tree_model.item(i)
            actual_categories.add(item.text())
            
        # 2. Check for missing
        missing = expected_categories - actual_categories
        assert not missing, f"Filter Tree is missing categories: {missing}. Did you forget to add the new field to the FilterWidget?"

    def test_filter_by_year_signal(self, widget):
        """Test that clicking a year emits filter_by_year"""
        # Mock years data
        widget.library_service.get_all_years.return_value = [2020, 2021]
        widget.populate() # Re-populate with years
        
        mock_slot = MagicMock()
        widget.filter_by_year.connect(mock_slot)
        
        # Traverse to find 2020
        # Roots: Perf, Comp, Lyr, Prod, Years
        # Index of Years is 4
        years_root = widget.tree_model.item(4)
        assert years_root.text() == "Years"
        
        # Decade 2020s
        decade_node = years_root.child(0)
        assert decade_node.text() == "2020s"
        
        # Year 2020
        year_node = decade_node.child(0) # or child(1) depending on sort
        # 2021, 2020 -> Sorted reverse? logic says sorted(decades keys, reverse=True). 
        # Inside decade: decades[d].append(year). Original list order [2020, 2021].
        # It just appends. So 2020 is first.
        
        # Find the node for 2020 explicitly just to be safe
        year_node = None
        for r in range(decade_node.rowCount()):
            if decade_node.child(r).text() == "2020":
                year_node = decade_node.child(r)
                break
        
        assert year_node is not None
        
        index = widget.tree_model.indexFromItem(year_node)
        widget._on_tree_clicked(index)
        
        mock_slot.assert_called_with(2020)
