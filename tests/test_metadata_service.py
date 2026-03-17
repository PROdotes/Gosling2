import pytest
from pathlib import Path
from src.services.metadata_service import MetadataService
from mutagen.id3 import ID3, TIT2, TPE1, TDRC, TIPL, TCOM
import shutil


@pytest.fixture
def silence_mp3(tmp_path):
    """Provides a fresh silence.mp3 for each test."""
    fixture_path = Path("tests/fixtures/silence.mp3")
    test_file = tmp_path / "test.mp3"
    shutil.copy(fixture_path, test_file)
    return test_file


def test_extract_metadata_raw_frames(silence_mp3):
    """LAW: MetadataService must extract raw frame IDs with list fidelity."""
    tags = ID3()
    tags.add(TIT2(encoding=3, text=["Test Title"]))
    tags.add(TPE1(encoding=3, text=["Artist 1\u0000Artist 2"]))
    tags.add(TDRC(encoding=3, text=["2024-03-16"]))
    tags.save(str(silence_mp3))

    service = MetadataService()
    metadata = service.extract_metadata(str(silence_mp3))

    assert "TIT2" in metadata
    assert metadata["TIT2"] == ["Test Title"]
    assert "TPE1" in metadata
    assert metadata["TPE1"] == ["Artist 1", "Artist 2"]
    assert "TDRC" in metadata
    assert metadata["TDRC"] == ["2024-03-16"]


def test_extract_metadata_complex_delimiters(silence_mp3):
    """LAW: Supported delimiters must be split into separate list items."""
    tags = ID3()
    # TCOM with ' / ' delimiter
    tags.add(TCOM(encoding=3, text=["Composer 1 / Composer 2"]))
    # Custom TXXX with '|||'
    from mutagen.id3 import TXXX

    tags.add(TXXX(encoding=3, desc="CUSTOM_LIST", text=["Item 1|||Item 2"]))
    tags.save(str(silence_mp3))

    service = MetadataService()
    metadata = service.extract_metadata(str(silence_mp3))

    assert metadata["TCOM"] == ["Composer 1", "Composer 2"]
    assert metadata["TXXX:CUSTOM_LIST"] == ["Item 1", "Item 2"]


def test_extract_metadata_tipl_resolution(silence_mp3):
    """LAW: TIPL people list must be resolved to clean names."""
    tags = ID3()
    # Involved People List (mutagen complex object)
    tags.add(
        TIPL(
            encoding=3, people=[["producer", "Producer A"], ["engineer", "Engineer B"]]
        )
    )
    tags.save(str(silence_mp3))

    service = MetadataService()
    metadata = service.extract_metadata(str(silence_mp3))

    assert "TIPL" in metadata
    assert "Producer A" in metadata["TIPL"]
    assert "Engineer B" in metadata["TIPL"]


def test_extract_metadata_invalid_file(tmp_path):
    """LAW: Handlers must return an empty dict for unparsable files."""
    file_path = tmp_path / "junk.mp3"
    file_path.write_bytes(b"Not an MP3 file content.")

    service = MetadataService()
    metadata = service.extract_metadata(str(file_path))
    assert metadata == {}


def test_extract_metadata_file_not_found():
    """LAW: Check for explicit FileNotFoundError."""
    service = MetadataService()
    with pytest.raises(FileNotFoundError):
        service.extract_metadata("ghost_file.mp3")


def test_extract_metadata_comprehensive_skrillex(silence_mp3):
    """LAW: Must handle the full complexity of modern electronic music tags (e.g. Skrillex)."""
    from mutagen.id3 import TXXX, TPUB, TCON, TLAN

    tags = ID3()
    # 1. Multi-artist with official null delimiter
    tags.add(TPE1(encoding=3, text=["Skrillex\u0000ISOxo"]))
    # 2. Key tracks
    tags.add(TIT2(encoding=3, text=["RATATA"]))
    # 3. Year
    tags.add(TDRC(encoding=3, text=["2023"]))
    # 4. Complex Involved People List (TIPL)
    tags.add(
        TIPL(
            encoding=3,
            people=[
                ["producer", "Skrillex"],
                ["producer", "ISOxo"],
                ["mixer", "Tom Norris"],
            ],
        )
    )
    # 5. Doubled Custom Frames (TXXX)
    tags.add(TXXX(encoding=3, desc="STATUS", text=["Released"]))
    tags.add(TXXX(encoding=3, desc="PRODUCER", text=["Skrillex|||ISOxo"]))
    # 6. Delimiter in standard frame (spaced slash)
    tags.add(TCOM(encoding=3, text=["Sonny Moore / Julian Isorena"]))

    # 7. Publisher, Genre, and Language (as requested)
    tags.add(TPUB(encoding=3, text=["OWSLA\u0000Atlantic"]))  # Multi-publisher
    tags.add(TCON(encoding=3, text=["Electronic / Trap"]))  # Multi-genre
    tags.add(TLAN(encoding=3, text=["eng"]))  # Language

    tags.save(str(silence_mp3))

    service = MetadataService()
    metadata = service.extract_metadata(str(silence_mp3))

    # Verify high-fidelity preservation
    assert metadata["TPE1"] == ["Skrillex", "ISOxo"]
    assert metadata["TIT2"] == ["RATATA"]
    assert metadata["TDRC"] == ["2023"]
    # TIPL should return ALL names involved
    assert "Skrillex" in metadata["TIPL"]
    assert "ISOxo" in metadata["TIPL"]
    assert "Tom Norris" in metadata["TIPL"]

    # Custom tags preserved with : descriptor
    assert metadata["TXXX:STATUS"] == ["Released"]
    # Verify ||| delimiter splitting
    assert metadata["TXXX:PRODUCER"] == ["Skrillex", "ISOxo"]
    # Verify / delimiter splitting
    assert metadata["TCOM"] == ["Sonny Moore", "Julian Isorena"]

    # Verify requested fields
    assert metadata["TPUB"] == ["OWSLA", "Atlantic"]
    assert metadata["TCON"] == ["Electronic", "Trap"]
    assert metadata["TLAN"] == ["eng"]


def test_extract_metadata_tagless_file(silence_mp3):
    """LAW: Must handle files with no metadata headers gracefully."""
    from mutagen.id3 import ID3

    # Physically strip all ID3 tags from the file to trigger fallback/None logic
    tags = ID3(str(silence_mp3))
    tags.delete()

    service = MetadataService()
    # This should hit the 'if tags is None' branch and EasyID3 fallback
    metadata = service.extract_metadata(str(silence_mp3))
    assert isinstance(metadata, dict)
    # Even if EasyID3 finds nothing, it should return an empty dict, not crash
    assert metadata == {}


def test_extract_metadata_skips_binary(silence_mp3):
    """LAW: APIC and other binary frames must be ignored to prevent table pollution."""
    from mutagen.id3 import ID3, APIC

    tags = ID3()
    tags.add(
        APIC(
            encoding=3, mime="image/jpeg", type=3, desc="Cover", data=b"fake_image_data"
        )
    )
    tags.add(TIT2(encoding=3, text=["Clean Title"]))
    tags.save(str(silence_mp3))

    service = MetadataService()
    metadata = service.extract_metadata(str(silence_mp3))

    # APIC should be missing, TIT2 should be there
    assert "APIC" not in metadata
    assert "TIT2" in metadata
    assert metadata["TIT2"] == ["Clean Title"]
