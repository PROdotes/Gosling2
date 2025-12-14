import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from src.presentation.widgets.filter_widget import FilterWidget
from src.data.repositories.base_repository import BaseRepository

# We need a headless QApplication for widget tests
@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])

def test_filter_widget_role_coverage(qapp, tmp_path):
    """
    Filter Widget Integrity Test:
    Ensures that the FilterWidget exposes a category for EVERY Role defined in the database.
    
    If a developer adds a new Role (e.g. 'Arranger') to the Roles table,
    they MUST add it to the FilterWidget. This test enforces that rule.
    """
    # 1. Get Actual Roles from DB (Source of Truth)
    db_path = tmp_path / "test_filter_integrity.db"
    repo = BaseRepository(str(db_path))
    
    with repo.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Name FROM Roles")
        db_roles = {row[0] for row in cursor.fetchall()}
    
    # 2. Inspect FilterWidget (The Implementation)
    # We inspect the 'populate' method logic by observing the tree model items
    service_mock = MagicMock()
    # Mock return values to be empty to avoid complex population, 
    # we just check the ROOT items (Categories)
    service_mock.get_contributors_by_role.return_value = [] 
    
    widget = FilterWidget(service_mock)
    widget.populate()
    
    # Extract categories from the tree model
    widget_categories = set()
    root = widget.tree_model.invisibleRootItem()
    for i in range(root.rowCount()):
        item = root.child(i)
        # Category Name (e.g. "Performers") -> We need to map to Role Name ("Performer")
        # The widget stores the Role Name in UserRole + 1. Let's retrieve that.
        role_data = item.data(257) # Qt.ItemDataRole.UserRole + 1 (256 + 1)
        if role_data:
            widget_categories.add(role_data)
        else:
            # Fallback map if data isn't set (it IS set in current impl)
            pass
            
    # 3. Assert Coverage
    missing_roles = db_roles - widget_categories
    
    # NOTE: "Producer" and "Lyricist" are default roles in BaseRepository but NOT in FilterWidget.
    # We EXPECT this to fail.
    assert not missing_roles, \
        f"FilterWidget is missing categories for Roles: {missing_roles}. " \
        "You added a Role to the DB but forgot to add it to the FilterWidget!"
