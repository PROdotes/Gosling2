import pytest
from src.services.metadata_parser import MetadataParser
from src.models.domain import SongCredit, Tag


@pytest.fixture
def parser():
    return MetadataParser()


def _assert_song_defaults(song, source_path="fake/path.mp3"):
    """Assert the invariant defaults every Song must have after parse."""
    assert song.id is None, f"Expected id=None, got {song.id}"
    assert song.type_id is None, f"Expected type_id=None, got {song.type_id}"
    assert song.audio_hash is None, f"Expected audio_hash=None, got {song.audio_hash}"
    assert (
        song.processing_status is None
    ), f"Expected processing_status=None, got {song.processing_status}"
    assert song.is_active is False, f"Expected is_active=False, got {song.is_active}"
    assert song.notes is None, f"Expected notes=None, got {song.notes}"
    assert song.isrc is None, f"Expected isrc=None, got {song.isrc}"
    assert (
        song.source_path == source_path
    ), f"Expected source_path='{source_path}', got '{song.source_path}'"


class TestParse:
    """MetadataParser.parse contracts."""

    def test_basic_fields(self, parser):
        """parse() must populate media_name, year, bpm, duration_ms from raw ID3 frames."""
        raw = {"TIT2": ["Fuze"], "TYER": ["2024"], "TBPM": ["128"], "TLEN": ["180"]}
        song = parser.parse(raw, "fake/path.mp3")

        assert (
            song.media_name == "Fuze"
        ), f"Expected media_name='Fuze', got '{song.media_name}'"
        assert song.year == 2024, f"Expected year=2024, got {song.year}"
        assert song.bpm == 128, f"Expected bpm=128, got {song.bpm}"
        assert (
            song.duration_s == 180.0
        ), f"Expected duration_s=180.0, got {song.duration_s}"
        assert (
            song.source_path == "fake/path.mp3"
        ), f"Expected source_path='fake/path.mp3', got '{song.source_path}'"
        assert song.credits == [], f"Expected no credits, got {song.credits}"
        assert song.tags == [], f"Expected no tags, got {song.tags}"
        assert song.albums == [], f"Expected no albums, got {song.albums}"
        assert song.publishers == [], f"Expected no publishers, got {song.publishers}"
        assert song.raw_tags == {}, f"Expected empty raw_tags, got {song.raw_tags}"
        _assert_song_defaults(song)

    def test_year_with_dash(self, parser):
        """parse() must split year on dash and cast the first segment to int."""
        raw = {"TYER": ["2024-03-16"]}
        song = parser.parse(raw, "fake/path.mp3")

        assert song.year == 2024, f"Expected year=2024, got {song.year}"
        assert song.media_name == "", f"Expected media_name='', got '{song.media_name}'"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.duration_s == 0.0, f"Expected duration_s=0.0, got {song.duration_ms}"

    def test_credits_deduplication(self, parser):
        """parse() must deduplicate credits while preserving first-seen order across TPE1 and TIPL."""
        raw = {"TPE1": ["Skrillex", "ISOxo"], "TIPL": ["Skrillex", "Someone Else"]}
        song = parser.parse(raw, "fake/path.mp3")

        performers = [c for c in song.credits if c.role_name == "Performer"]
        producers = [c for c in song.credits if c.role_name == "Producer"]

        assert len(performers) == 2, f"Expected 2 performers, got {len(performers)}"
        assert (
            performers[0].display_name == "Skrillex"
        ), f"Expected performer[0]='Skrillex', got '{performers[0].display_name}'"
        assert (
            performers[1].display_name == "ISOxo"
        ), f"Expected performer[1]='ISOxo', got '{performers[1].display_name}'"

        assert len(producers) == 2, f"Expected 2 producers, got {len(producers)}"
        assert (
            producers[0].display_name == "Skrillex"
        ), f"Expected producer[0]='Skrillex', got '{producers[0].display_name}'"
        assert (
            producers[1].display_name == "Someone Else"
        ), f"Expected producer[1]='Someone Else', got '{producers[1].display_name}'"

        assert (
            len(song.credits) == 4
        ), f"Expected 4 total credits, got {len(song.credits)}"
        for credit in song.credits:
            assert isinstance(
                credit, SongCredit
            ), f"Expected SongCredit, got {type(credit)}"
            assert (
                credit.source_id is None
            ), f"Expected source_id=None, got {credit.source_id}"
            assert (
                credit.name_id is None
            ), f"Expected name_id=None, got {credit.name_id}"
            assert (
                credit.identity_id is None
            ), f"Expected identity_id=None, got {credit.identity_id}"
            assert (
                credit.role_id is None
            ), f"Expected role_id=None, got {credit.role_id}"
            assert (
                credit.is_primary is False
            ), f"Expected is_primary=False, got {credit.is_primary}"

    def test_custom_tags(self, parser):
        """parse() must route TCON to Genre tags and TMOO to Mood tags."""
        raw = {"TCON": ["Dubstep", "Electronic"], "TMOO": ["Aggressive"]}
        song = parser.parse(raw, "fake/path.mp3")

        genres = [t for t in song.tags if t.category == "Genre"]
        moods = [t for t in song.tags if t.category == "Mood"]

        assert len(genres) == 2, f"Expected 2 genre tags, got {len(genres)}"
        assert (
            genres[0].name == "Dubstep"
        ), f"Expected genre[0]='Dubstep', got '{genres[0].name}'"
        assert (
            genres[1].name == "Electronic"
        ), f"Expected genre[1]='Electronic', got '{genres[1].name}'"

        assert len(moods) == 1, f"Expected 1 mood tag, got {len(moods)}"
        assert (
            moods[0].name == "Aggressive"
        ), f"Expected mood='Aggressive', got '{moods[0].name}'"

        assert len(song.tags) == 3, f"Expected 3 total tags, got {len(song.tags)}"
        for tag in song.tags:
            assert isinstance(tag, Tag), f"Expected Tag, got {type(tag)}"
            assert tag.id is None, f"Expected tag id=None, got {tag.id}"
            assert (
                tag.is_primary is False
            ), f"Expected is_primary=False, got {tag.is_primary}"

    def test_safe_integer_casting(self, parser):
        """parse() must extract leading digits from messy year and return None for non-numeric BPM."""
        raw = {
            "TYER": ["2024 (Remaster)"],
            "TDRC": ["2023"],
            "TBPM": ["not a number"],
        }
        song = parser.parse(raw, "fake/path.mp3")

        assert song.year == 2023, f"Expected year=2023, got {song.year}"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.media_name == "", f"Expected media_name='', got '{song.media_name}'"
        assert song.duration_s == 0.0, f"Expected duration_s=0.0, got {song.duration_ms}"

    def test_album_creation(self, parser):
        """parse() must create SongAlbum from TALB and Publisher objects from TPUB."""
        raw = {"TALB": ["Quest for Fire"], "TPUB": ["Atlantic", "OWSLA"]}
        song = parser.parse(raw, "fake/path.mp3")

        assert len(song.albums) == 1, f"Expected 1 album, got {len(song.albums)}"
        album = song.albums[0]
        assert (
            album.album_title == "Quest for Fire"
        ), f"Expected album_title='Quest for Fire', got '{album.album_title}'"
        assert (
            album.source_id is None
        ), f"Expected source_id=None, got {album.source_id}"
        assert album.album_id is None, f"Expected album_id=None, got {album.album_id}"
        assert (
            album.is_primary is True
        ), f"Expected is_primary=True, got {album.is_primary}"
        assert (
            album.track_number is None
        ), f"Expected track_number=None, got {album.track_number}"
        assert (
            album.disc_number is None
        ), f"Expected disc_number=None, got {album.disc_number}"
        assert (
            album.album_type is None
        ), f"Expected album_type=None, got {album.album_type}"
        assert (
            album.release_year is None
        ), f"Expected release_year=None, got {album.release_year}"
        assert (
            album.album_publishers == []
        ), f"Expected empty album_publishers, got {album.album_publishers}"
        assert album.credits == [], f"Expected empty album credits, got {album.credits}"

        assert (
            len(song.publishers) == 2
        ), f"Expected 2 publishers, got {len(song.publishers)}"
        pub_names = [p.name for p in song.publishers]
        assert pub_names == [
            "Atlantic",
            "OWSLA",
        ], f"Expected publishers ['Atlantic','OWSLA'], got {pub_names}"
        for pub in song.publishers:
            assert pub.id is None, f"Expected pub id=None, got {pub.id}"
            assert (
                pub.parent_id is None
            ), f"Expected pub parent_id=None, got {pub.parent_id}"
            assert (
                pub.parent_name is None
            ), f"Expected pub parent_name=None, got {pub.parent_name}"
            assert (
                pub.sub_publishers == []
            ), f"Expected empty sub_publishers, got {pub.sub_publishers}"

    def test_dynamic_tags(self, parser):
        """parse() must turn unknown TXXX:Descriptor frames into dynamic Tags and keep UNKNOWN as raw_tags."""
        raw = {
            "TXXX:Festival": ["Dora"],
            "TXXX:Dog": ["Labrador"],
            "UNKNOWN": ["Some Value"],
        }
        song = parser.parse(raw, "fake/path.mp3")

        festivals = [t for t in song.tags if t.category == "Festival"]
        dogs = [t for t in song.tags if t.category == "Dog"]

        assert len(festivals) == 1, f"Expected 1 Festival tag, got {len(festivals)}"
        assert (
            festivals[0].name == "Dora"
        ), f"Expected festival name='Dora', got '{festivals[0].name}'"
        assert len(dogs) == 1, f"Expected 1 Dog tag, got {len(dogs)}"
        assert (
            dogs[0].name == "Labrador"
        ), f"Expected dog name='Labrador', got '{dogs[0].name}'"

        assert song.raw_tags == {
            "UNKNOWN": ["Some Value"]
        }, f"Expected raw_tags={{'UNKNOWN': ['Some Value']}}, got {song.raw_tags}"

    def test_empty_fields_strict(self, parser):
        """parse() with empty metadata must produce no defaults, no guessed titles, no assumed disc numbers."""
        raw = {}
        song = parser.parse(raw, "fake/path.mp3")

        assert song.media_name == "", f"Expected media_name='', got '{song.media_name}'"
        assert song.year is None, f"Expected year=None, got {song.year}"
        assert song.bpm is None, f"Expected bpm=None, got {song.bpm}"
        assert song.duration_s == 0.0, f"Expected duration_s=0.0, got {song.duration_ms}"
        assert song.credits == [], f"Expected no credits, got {song.credits}"
        assert song.tags == [], f"Expected no tags, got {song.tags}"
        assert song.albums == [], f"Expected no albums, got {song.albums}"
        assert song.publishers == [], f"Expected no publishers, got {song.publishers}"
        assert song.raw_tags == {}, f"Expected empty raw_tags, got {song.raw_tags}"
        _assert_song_defaults(song)

    def test_no_txxx_config_borrowing(self, parser):
        """parse() must treat TXXX:DESCRIPTOR as dynamic Tag, not borrow base TXXX config."""
        raw = {"TXXX:Pure": ["Strict"]}
        song = parser.parse(raw, "fake/path.mp3")

        pures = [t for t in song.tags if t.category == "Pure"]
        assert len(pures) == 1, f"Expected 1 Pure tag, got {len(pures)}"
        assert (
            pures[0].name == "Strict"
        ), f"Expected Pure tag name='Strict', got '{pures[0].name}'"

        assert (
            "User defined text information frame" not in song.raw_tags
        ), f"Expected 'User defined text information frame' absent from raw_tags, got keys {list(song.raw_tags.keys())}"


class TestParserConfig:
    """MetadataParser constructor contracts."""

    def test_config_not_found(self):
        """MetadataParser must degrade gracefully with empty config when JSON path is invalid."""
        p = MetadataParser(json_path="non_existent_config_file.json")
        assert p.config == {}, f"Expected empty config, got {p.config}"
