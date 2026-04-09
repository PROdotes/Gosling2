import shutil
import pytest
from pathlib import Path
from mutagen.id3 import ID3, APIC, TXXX

from src.services.metadata_writer import MetadataWriter
from src.models.domain import Song, SongCredit, Tag, SongAlbum, Publisher, AlbumCredit

SILENCE_MP3 = Path(__file__).parent.parent / "fixtures" / "silence.mp3"


@pytest.fixture
def mp3(tmp_path):
    """Fresh copy of silence.mp3 with all ID3 tags stripped, for each test."""
    from mutagen.mp3 import MP3

    dst = tmp_path / "test.mp3"
    shutil.copy(SILENCE_MP3, dst)
    MP3(str(dst)).delete()
    return dst


@pytest.fixture
def writer():
    return MetadataWriter()


def _bare_song(path: Path, **kwargs) -> Song:
    """Minimal valid Song with no optional fields set, unless overridden."""
    defaults = dict(
        media_name="Test Song",
        source_path=str(path),
        duration_s=1.0,
        processing_status=0,
        year=None,
        bpm=None,
        isrc=None,
        notes=None,
        credits=[],
        tags=[],
        albums=[],
        publishers=[],
    )
    defaults.update(kwargs)
    return Song(**defaults)


# ---------------------------------------------------------------------------
# Scalars
# ---------------------------------------------------------------------------


class TestWriteMetadataScalars:

    def test_title_written(self, writer, mp3):
        song = _bare_song(mp3, media_name="Neon Pulse")
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TIT2" in tags, "Expected TIT2 frame to be written"
        assert (
            str(tags["TIT2"]) == "Neon Pulse"
        ), f"Expected 'Neon Pulse', got '{tags['TIT2']}'"

    def test_year_written(self, writer, mp3):
        song = _bare_song(mp3, year=2023)
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TDRC" in tags, "Expected TDRC frame to be written"
        assert str(tags["TDRC"]) == "2023", f"Expected '2023', got '{tags['TDRC']}'"

    def test_bpm_written(self, writer, mp3):
        song = _bare_song(mp3, bpm=140)
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TBPM" in tags, "Expected TBPM frame to be written"
        assert str(tags["TBPM"]) == "140", f"Expected '140', got '{tags['TBPM']}'"

    def test_isrc_written(self, writer, mp3):
        song = _bare_song(mp3, isrc="GBABC1234567")
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TSRC" in tags, "Expected TSRC frame to be written"
        assert (
            str(tags["TSRC"]) == "GBABC1234567"
        ), f"Expected 'GBABC1234567', got '{tags['TSRC']}'"

    def test_notes_written_as_comm(self, writer, mp3):
        song = _bare_song(mp3, notes="Some note")
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        comm_frames = tags.getall("COMM")
        assert comm_frames, "Expected at least one COMM frame"
        texts = [str(t) for frame in comm_frames for t in frame.text]
        assert "Some note" in texts, f"Expected 'Some note' in COMM frames, got {texts}"

    def test_null_year_not_written(self, writer, mp3):
        song = _bare_song(mp3, year=None)
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TDRC" not in tags, "Expected TDRC to be absent when year is None"

    def test_null_bpm_not_written(self, writer, mp3):
        song = _bare_song(mp3, bpm=None)
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TBPM" not in tags, "Expected TBPM to be absent when bpm is None"

    def test_null_isrc_not_written(self, writer, mp3):
        song = _bare_song(mp3, isrc=None)
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TSRC" not in tags, "Expected TSRC to be absent when isrc is None"


# ---------------------------------------------------------------------------
# Credits
# ---------------------------------------------------------------------------


class TestWriteMetadataCredits:

    def test_performer_written_as_tpe1(self, writer, mp3):
        song = _bare_song(
            mp3, credits=[SongCredit(role_name="Performer", display_name="Antigravity")]
        )
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TPE1" in tags, "Expected TPE1 frame for Performer credit"
        assert (
            "Antigravity" in tags["TPE1"].text
        ), f"Expected 'Antigravity' in TPE1, got {tags['TPE1'].text}"

    def test_multiple_performers_in_single_frame(self, writer, mp3):
        song = _bare_song(
            mp3,
            credits=[
                SongCredit(role_name="Performer", display_name="Artist A"),
                SongCredit(role_name="Performer", display_name="Artist B"),
            ],
        )
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TPE1" in tags, "Expected TPE1 frame"
        assert (
            "Artist A" in tags["TPE1"].text
        ), f"Expected 'Artist A' in TPE1, got {tags['TPE1'].text}"
        assert (
            "Artist B" in tags["TPE1"].text
        ), f"Expected 'Artist B' in TPE1, got {tags['TPE1'].text}"

    def test_composer_written_as_tcom(self, writer, mp3):
        song = _bare_song(
            mp3, credits=[SongCredit(role_name="Composer", display_name="Bach")]
        )
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TCOM" in tags, "Expected TCOM frame for Composer credit"
        assert (
            "Bach" in tags["TCOM"].text
        ), f"Expected 'Bach' in TCOM, got {tags['TCOM'].text}"

    def test_unmapped_role_written_as_txxx(self, writer, mp3):
        song = _bare_song(
            mp3, credits=[SongCredit(role_name="Remixer", display_name="DJ X")]
        )
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        txxx_frames = {f.desc: f.text for f in tags.getall("TXXX")}
        assert (
            "Remixer" in txxx_frames
        ), f"Expected TXXX:Remixer, got keys: {list(txxx_frames.keys())}"
        assert (
            "DJ X" in txxx_frames["Remixer"]
        ), f"Expected 'DJ X' in TXXX:Remixer, got {txxx_frames['Remixer']}"

    def test_duplicate_performer_names_deduplicated(self, writer, mp3):
        song = _bare_song(
            mp3,
            credits=[
                SongCredit(role_name="Performer", display_name="Artist A"),
                SongCredit(role_name="Performer", display_name="Artist A"),
            ],
        )
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert (
            tags["TPE1"].text.count("Artist A") == 1
        ), f"Expected 'Artist A' once in TPE1, got {tags['TPE1'].text}"

    def test_no_credits_no_tpe1(self, writer, mp3):
        song = _bare_song(mp3, credits=[])
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TPE1" not in tags, "Expected no TPE1 frame when credits list is empty"


# ---------------------------------------------------------------------------
# Tags (Genre, Mood, etc.)
# ---------------------------------------------------------------------------


class TestWriteMetadataTags:

    def test_genre_written_as_tcon(self, writer, mp3):
        song = _bare_song(mp3, tags=[Tag(name="Techno", category="Genre")])
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TCON" in tags, "Expected TCON frame for Genre tag"
        assert (
            "Techno" in tags["TCON"].text
        ), f"Expected 'Techno' in TCON, got {tags['TCON'].text}"

    def test_multiple_genres_in_single_frame(self, writer, mp3):
        song = _bare_song(
            mp3,
            tags=[
                Tag(name="Techno", category="Genre"),
                Tag(name="House", category="Genre"),
            ],
        )
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TCON" in tags, "Expected TCON frame"
        assert (
            "Techno" in tags["TCON"].text
        ), f"Expected 'Techno' in TCON, got {tags['TCON'].text}"
        assert (
            "House" in tags["TCON"].text
        ), f"Expected 'House' in TCON, got {tags['TCON'].text}"

    def test_unmapped_category_written_as_txxx(self, writer, mp3):
        song = _bare_song(mp3, tags=[Tag(name="Ballad", category="Subgenre")])
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        txxx_frames = {f.desc: f.text for f in tags.getall("TXXX")}
        assert (
            "Subgenre" in txxx_frames
        ), f"Expected TXXX:Subgenre, got keys: {list(txxx_frames.keys())}"
        assert (
            "Ballad" in txxx_frames["Subgenre"]
        ), f"Expected 'Ballad' in TXXX:Subgenre, got {txxx_frames['Subgenre']}"

    def test_no_tags_no_tcon(self, writer, mp3):
        song = _bare_song(mp3, tags=[])
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TCON" not in tags, "Expected no TCON frame when tags list is empty"


# ---------------------------------------------------------------------------
# Albums
# ---------------------------------------------------------------------------


class TestWriteMetadataAlbums:

    def test_album_title_written_as_talb(self, writer, mp3):
        song = _bare_song(
            mp3, albums=[SongAlbum(album_title="Artificial Intelligence")]
        )
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TALB" in tags, "Expected TALB frame"
        assert (
            str(tags["TALB"]) == "Artificial Intelligence"
        ), f"Expected 'Artificial Intelligence', got '{tags['TALB']}'"

    def test_track_number_written_as_trck(self, writer, mp3):
        song = _bare_song(mp3, albums=[SongAlbum(album_title="Album", track_number=3)])
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TRCK" in tags, "Expected TRCK frame"
        assert str(tags["TRCK"]) == "3", f"Expected '3', got '{tags['TRCK']}'"

    def test_disc_number_written_as_tpos(self, writer, mp3):
        song = _bare_song(mp3, albums=[SongAlbum(album_title="Album", disc_number=2)])
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TPOS" in tags, "Expected TPOS frame"
        assert str(tags["TPOS"]) == "2", f"Expected '2', got '{tags['TPOS']}'"

    def test_album_performer_written_as_tpe2(self, writer, mp3):
        album_credit = AlbumCredit(role_name="Performer", display_name="Band Name")
        song = _bare_song(
            mp3, albums=[SongAlbum(album_title="Album", credits=[album_credit])]
        )
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TPE2" in tags, "Expected TPE2 frame for album Performer"
        assert (
            "Band Name" in tags["TPE2"].text
        ), f"Expected 'Band Name' in TPE2, got {tags['TPE2'].text}"

    def test_no_track_number_no_trck(self, writer, mp3):
        song = _bare_song(
            mp3, albums=[SongAlbum(album_title="Album", track_number=None)]
        )
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TRCK" not in tags, "Expected no TRCK frame when track_number is None"

    def test_no_albums_no_talb(self, writer, mp3):
        song = _bare_song(mp3, albums=[])
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TALB" not in tags, "Expected no TALB frame when albums list is empty"

    def test_only_first_album_written(self, writer, mp3):
        song = _bare_song(
            mp3,
            albums=[
                SongAlbum(album_title="First Album"),
                SongAlbum(album_title="Second Album"),
            ],
        )
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert (
            str(tags["TALB"]) == "First Album"
        ), f"Expected only first album 'First Album', got '{tags['TALB']}'"


# ---------------------------------------------------------------------------
# Publishers
# ---------------------------------------------------------------------------


class TestWriteMetadataPublishers:

    def test_publisher_written_as_tpub(self, writer, mp3):
        song = _bare_song(mp3, publishers=[Publisher(name="ASCAP")])
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TPUB" in tags, "Expected TPUB frame"
        assert (
            "ASCAP" in tags["TPUB"].text
        ), f"Expected 'ASCAP' in TPUB, got {tags['TPUB'].text}"

    def test_multiple_publishers(self, writer, mp3):
        song = _bare_song(
            mp3, publishers=[Publisher(name="ASCAP"), Publisher(name="BMI")]
        )
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert "TPUB" in tags, "Expected TPUB frame"
        assert (
            "ASCAP" in tags["TPUB"].text
        ), f"Expected 'ASCAP' in TPUB, got {tags['TPUB'].text}"
        assert (
            "BMI" in tags["TPUB"].text
        ), f"Expected 'BMI' in TPUB, got {tags['TPUB'].text}"

    def test_no_publishers_no_tpub(self, writer, mp3):
        song = _bare_song(mp3, publishers=[])
        writer.write_metadata(song)
        tags = ID3(str(mp3))
        assert (
            "TPUB" not in tags
        ), "Expected no TPUB frame when publishers list is empty"


# ---------------------------------------------------------------------------
# Frame Preservation
# ---------------------------------------------------------------------------


class TestWriteMetadataPreservesFrames:

    def test_unrelated_txxx_preserved(self, writer, mp3):
        # Plant a TXXX:SomeOtherTool frame before writing
        existing = ID3()
        existing.add(TXXX(encoding=3, desc="SomeOtherTool", text=["external value"]))
        existing.save(str(mp3), v2_version=4)

        song = _bare_song(mp3, tags=[Tag(name="Dark", category="Mood")])
        writer.write_metadata(song)

        tags = ID3(str(mp3))
        txxx_frames = {f.desc: f.text for f in tags.getall("TXXX")}
        assert (
            "SomeOtherTool" in txxx_frames
        ), f"Expected unrelated TXXX:SomeOtherTool to survive, got keys: {list(txxx_frames.keys())}"
        assert txxx_frames["SomeOtherTool"] == [
            "external value"
        ], f"Expected 'external value' unchanged, got {txxx_frames['SomeOtherTool']}"

    def test_apic_preserved(self, writer, mp3):
        # Plant an APIC frame before writing
        existing = ID3()
        existing["APIC:"] = APIC(
            encoding=3, mime="image/jpeg", type=3, desc="", data=b"\xff\xd8\xff"
        )
        existing.save(str(mp3), v2_version=4)

        song = _bare_song(mp3, media_name="Title")
        writer.write_metadata(song)

        tags = ID3(str(mp3))
        apic_frames = tags.getall("APIC")
        assert apic_frames, "Expected APIC frame to survive write_metadata"
        assert (
            apic_frames[0].data == b"\xff\xd8\xff"
        ), "Expected APIC data to be unchanged"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TestWriteMetadataErrors:

    def test_missing_file_raises_file_not_found(self, writer, tmp_path):
        song = _bare_song(tmp_path / "nonexistent.mp3")
        with pytest.raises(FileNotFoundError):
            writer.write_metadata(song)

    def test_non_mp3_file_skipped_silently(self, writer, tmp_path):
        flac = tmp_path / "audio.flac"
        flac.write_bytes(b"\x00" * 16)
        song = _bare_song(flac, media_name="Title")
        # Must not raise
        writer.write_metadata(song)
