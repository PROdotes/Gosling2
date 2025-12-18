import pytest
from src.core import yellberus

def test_strict_filter_coverage():
    """
    STRICT Filter Coverage (Yellberus version):
    Ensures that all filterable fields in Yellberus are properly configured.
    
    Logic:
    1. Get all filterable fields from Yellberus
    2. Verify each has a valid filter_type
    3. Verify fields with grouping_function are properly configured
    """
    
    filterable_fields = yellberus.get_filterable_fields()
    
    # Should have some filterable fields
    assert len(filterable_fields) > 0, "No filterable fields defined in Yellberus"
    
    for field in filterable_fields:
        # Each filterable field must have a filter_type
        assert field.filter_type in ["list", "range", "boolean"], \
            f"Field '{field.name}' has invalid filter_type: {field.filter_type}"
        
        # Fields with grouping must have a callable grouping_function
        if field.grouping_function is not None:
            assert callable(field.grouping_function), \
                f"Field '{field.name}' has non-callable grouping_function"
            
            # Test the grouping function doesn't crash
            try:
                result = field.grouping_function(2024)
                assert isinstance(result, str), \
                    f"Field '{field.name}' grouping_function should return string"
            except Exception as e:
                pytest.fail(f"Field '{field.name}' grouping_function raised: {e}")

def test_filterable_fields_have_ui_headers():
    """Ensure all filterable fields have proper UI headers for display."""
    for field in yellberus.get_filterable_fields():
        assert field.ui_header, f"Filterable field '{field.name}' missing ui_header"
        assert len(field.ui_header) > 0, f"Filterable field '{field.name}' has empty ui_header"
