import pytest
from unittest.mock import MagicMock
from src.presentation.widgets.metadata_viewer_dialog import MetadataViewerDialog
from src.core import yellberus

def test_metadata_viewer_strict_mapping(qtbot):
    """
    STRICT Metadata Viewer Mapping:
    Ensures that MetadataViewerDialog contains a mapping for EVERY portable column 
    defined in Yellberus (excluding local-only fields like IDs or Paths).
    
    If 'Genre' is added to Yellberus and marked as portable=True, 
    this test will fail until it's added to MetadataViewerDialog.mapped_fields.
    """
    # 1. Inspect MetadataViewerDialog Schema Logic
    mock_file = MagicMock()
    mock_db = MagicMock()
    
    # Create dialog to inspect its schema rules
    dlg = MetadataViewerDialog(mock_file, mock_db)
    
    # Extract the set of SONG ATTRIBUTES it maps to.
    # mapped_fields format: (Label, SongAttribute, [ID3Tags])
    mapped_attributes = {entry[1] for entry in dlg.mapped_fields}
    
    # 2. Get Portable Fields from Yellberus
    # Portable fields are those that can/should live in ID3 tags.
    # We ignore file_id, path, type_id etc if marked portable=False.
    portable_field_names = [f.name for f in yellberus.FIELDS if f.portable]
    
    # 3. Handle Special Display Attribute Mappings
    # The Dialog might use a presentation property (e.g. 'formatted_duration' instead of 'duration')
    attribute_overrides = {
        "duration": "formatted_duration"
    }

    # 4. Verify Coverage
    missing_fields = []
    for field_name in portable_field_names:
        expected_attr = attribute_overrides.get(field_name, field_name)
        if expected_attr not in mapped_attributes:
            missing_fields.append(field_name)
            
    if missing_fields:
        pytest.fail(
            f"MetadataViewerDialog is missing mapping for Yellberus portable fields: {missing_fields}. "
            "Update MetadataViewerDialog.mapped_fields to ensure users can view/sync these tags."
        )

    # 5. Verify No "Dead" Mappings (Optional but good)
    # Ensure every attribute mapped in Dialog actually exists in Yellberus 
    # (or is a known presentation override)
    all_yellberus_names = {f.name for f in yellberus.FIELDS}
    yellberus_overrides_rev = {v: k for k, v in attribute_overrides.items()}
    
    for _, attr, _ in dlg.mapped_fields:
        original_name = yellberus_overrides_rev.get(attr, attr)
        # Exception: album_artists is a model-only field for now, not in DB yet?
        if attr == "album_artists":
            continue
            
        assert original_name in all_yellberus_names, \
            f"MetadataViewerDialog maps to unknown attribute '{attr}' (not in Yellberus)."
