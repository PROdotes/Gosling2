from src.models.metadata_frames import ID3FrameConfig
from src.services.metadata_frames_reader import load_id3_frames
import json


def test_id3_frame_config_new_attributes():
    """Verifies that the model accepts the new reactive attributes."""
    config = ID3FrameConfig(
        description="Test Frame",
        field="test_field",
        skip_read=True,
        skip_write=True,
        role="Performer",
    )
    assert config.skip_read is True
    assert config.skip_write is True
    assert config.role == "Performer"


def test_config_loading_with_new_attributes(tmp_path):
    """Verifies that load_id3_frames correctly parses the updated JSON structure."""
    config_data = {
        "TPE1": {
            "description": "Artist",
            "field": "artist",
            "type": "list",
            "role": "Performer",
        },
        "APIC": {"description": "Cover", "skip_read": True},
        "TXXX:STATUS": {
            "description": "Status",
            "field": "processing_status",
            "skip_write": True,
            "internal_only": True,
        },
    }

    config_file = tmp_path / "test_frames.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    mapping = load_id3_frames(str(config_file))

    assert mapping["TPE1"].role == "Performer"
    assert mapping["APIC"].skip_read is True
    assert mapping["TXXX:STATUS"].skip_write is True
    assert mapping["TXXX:STATUS"].internal_only is True
