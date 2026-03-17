import pytest
from src.services.metadata_parser import MetadataParser


@pytest.fixture
def parser():
    return MetadataParser()


def test_parse_basic_fields(parser):
    raw = {"TIT2": ["Fuze"], "TYER": ["2024"], "TBPM": ["128"], "TLEN": ["180000"]}
    song = parser.parse(raw, "fake/path.mp3")

    assert song.media_name == "Fuze"
    assert song.year == 2024
    assert song.bpm == 128
    assert song.duration_ms == 180000
    assert song.source_path == "fake/path.mp3"


def test_parse_year_with_dash(parser):
    """Cover metadata_parser dash splitting logic."""
    raw = {"TYER": ["2024-03-16"]}
    song = parser.parse(raw, "fake/path.mp3")
    assert song.year == 2024


def test_parse_credits_deduplication(parser):
    # Simulate frame doubling: artist in TPE1 and a custom TIPL list
    raw = {"TPE1": ["Skrillex", "ISOxo"], "TIPL": ["Skrillex", "Someone Else"]}
    song = parser.parse(raw, "fake/path.mp3")

    performers = [c.display_name for c in song.credits if c.role_name == "Performer"]
    producers = [c.display_name for c in song.credits if c.role_name == "Producer"]

    assert "Skrillex" in performers
    assert "ISOxo" in performers
    assert "Skrillex" in producers
    assert "Someone Else" in producers
    assert len(song.credits) == 4


def test_parse_custom_tags(parser):
    raw = {"TCON": ["Dubstep", "Electronic"], "TMOO": ["Aggressive"]}
    song = parser.parse(raw, "fake/path.mp3")

    genres = [t.name for t in song.tags if t.category == "Genre"]
    moods = [t.name for t in song.tags if t.category == "Mood"]

    assert "Dubstep" in genres
    assert "Electronic" in genres
    assert "Aggressive" in moods
    assert len(song.tags) == 3


def test_safe_integer_casting(parser):
    raw = {
        "TYER": ["2024 (Remaster)"],
        "TDRC": ["2023"],  # Standard year frame
        "TBPM": ["not a number"],
    }
    song = parser.parse(raw, "fake/path.mp3")

    assert song.year == 2023  # TDRC is usually preferred or parsed correctly here
    assert song.bpm is None


def test_album_creation(parser):
    raw = {"TALB": ["Quest for Fire"], "TPUB": ["Atlantic", "OWSLA"]}
    song = parser.parse(raw, "fake/path.mp3")

    assert len(song.albums) == 1
    assert song.albums[0].album_title == "Quest for Fire"

    assert len(song.publishers) == 2
    pub_names = [p.name for p in song.publishers]
    assert "Atlantic" in pub_names
    assert "OWSLA" in pub_names


def test_parse_dynamic_tags(parser):
    """Verify that unknown TXXX:Descriptor frames are turned into dynamic Tags."""
    raw = {
        "TXXX:Festival": ["Dora"],
        "TXXX:Dog": ["Labrador"],
        "UNKNOWN": ["Some Value"],  # No descriptor, should go to raw_tags
    }
    song = parser.parse(raw, "fake/path.mp3")

    # Check dynamic tags
    festivals = [t.name for t in song.tags if t.category == "Festival"]
    dogs = [t.name for t in song.tags if t.category == "Dog"]

    assert "Dora" in festivals
    assert "Labrador" in dogs

    # Check raw_tags fallback
    assert song.raw_tags["UNKNOWN"] == ["Some Value"]


def test_parser_config_not_found():
    """Cover metadata_parser.py: 33-34 (Config not found)."""
    p = MetadataParser(json_path="non_existent_config_file.json")
    assert p.config == {}
