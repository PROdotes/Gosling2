import pytest
from src.presentation.widgets.filter_widget import FilterWidget

@pytest.fixture
def filter_widget(qtbot, mock_widget_deps):
    """Fixture for FilterWidget with mocked library service."""
    deps = mock_widget_deps
    widget = FilterWidget(deps['library_service'])
    qtbot.addWidget(widget)
    return widget

class TestFilterWidget:
    """
    Minimal smoke tests for FilterWidget.
    
    Detailed structural testing has been deprioritized to focus on 
    application stability and core user workflows first.
    """

    def test_widget_initialization(self, filter_widget):
        """Verify the widget can be instantiated without crashing."""
        assert filter_widget is not None

    def test_populate_does_not_crash(self, filter_widget):
        """Verify populate() runs safely (smoke test)."""
        try:
            filter_widget.populate()
        except Exception as e:
            pytest.fail(f"FilterWidget.populate() crashed: {e}")
