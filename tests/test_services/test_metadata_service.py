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


class TestMetadataServiceExtractMetadata:
    def test_extract_metadata_raw_frames(self, silence_mp3):
        """MetadataService.extract_metadata must return raw frame IDs as lists with string fidelity."""
        tags = ID3()
        tags.add(TIT2(encoding=3, text=["Test Title"]))
        tags.add(TPE1(encoding=3, text=["Artist 1\u0000Artist 2"]))
        tags.add(TDRC(encoding=3, text=["2024-03-16"]))
        tags.save(str(silence_mp3))

        service = MetadataService()
        metadata = service.extract_metadata(str(silence_mp3))

        assert isinstance(metadata, dict), f"Expected dict, got {type(metadata)}"
        assert (
            "TIT2" in metadata
        ), f"Expected 'TIT2' in metadata keys, got {list(metadata.keys())}"
        assert metadata["TIT2"] == [
            "Test Title"
        ], f"Expected TIT2=['Test Title'], got {metadata['TIT2']}"
        assert (
            "TPE1" in metadata
        ), f"Expected 'TPE1' in metadata keys, got {list(metadata.keys())}"
        assert metadata["TPE1"] == [
            "Artist 1",
            "Artist 2",
        ], f"Expected TPE1=['Artist 1','Artist 2'], got {metadata['TPE1']}"
        assert (
            "TDRC" in metadata
        ), f"Expected 'TDRC' in metadata keys, got {list(metadata.keys())}"
        assert metadata["TDRC"] == [
            "2024-03-16"
        ], f"Expected TDRC=['2024-03-16'], got {metadata['TDRC']}"
        assert (
            "TLEN" in metadata
        ), f"Expected 'TLEN' injection from stream info, got {list(metadata.keys())}"
        # silence.mp3 is 2.27s
        assert float(metadata["TLEN"][0]) > 2.0

    def test_extract_metadata_complex_delimiters(self, silence_mp3):
        """Supported delimiters (' / ' and '|||') must be split into separate list items."""
        tags = ID3()
        tags.add(TCOM(encoding=3, text=["Composer 1 / Composer 2"]))
        from mutagen.id3 import TXXX

        tags.add(TXXX(encoding=3, desc="CUSTOM_LIST", text=["Item 1|||Item 2"]))
        tags.save(str(silence_mp3))

        service = MetadataService()
        metadata = service.extract_metadata(str(silence_mp3))

        assert (
            "TCOM" in metadata
        ), f"Expected 'TCOM' in metadata keys, got {list(metadata.keys())}"
        assert metadata["TCOM"] == [
            "Composer 1",
            "Composer 2",
        ], f"Expected TCOM=['Composer 1','Composer 2'], got {metadata['TCOM']}"
        assert (
            "TXXX:CUSTOM_LIST" in metadata
        ), f"Expected 'TXXX:CUSTOM_LIST' in metadata keys, got {list(metadata.keys())}"
        assert metadata["TXXX:CUSTOM_LIST"] == [
            "Item 1",
            "Item 2",
        ], f"Expected TXXX:CUSTOM_LIST=['Item 1','Item 2'], got {metadata['TXXX:CUSTOM_LIST']}"

    def test_extract_metadata_tipl_resolution(self, silence_mp3):
        """TIPL people list must be resolved to clean name strings."""
        tags = ID3()
        tags.add(
            TIPL(
                encoding=3,
                people=[["producer", "Producer A"], ["engineer", "Engineer B"]],
            )
        )
        tags.save(str(silence_mp3))

        service = MetadataService()
        metadata = service.extract_metadata(str(silence_mp3))

        assert (
            "TIPL" in metadata
        ), f"Expected 'TIPL' in metadata keys, got {list(metadata.keys())}"
        assert isinstance(
            metadata["TIPL"], list
        ), f"Expected TIPL to be list, got {type(metadata['TIPL'])}"
        assert (
            len(metadata["TIPL"]) == 2
        ), f"Expected 2 TIPL entries, got {len(metadata['TIPL'])}"
        assert (
            "Producer A" in metadata["TIPL"]
        ), f"Expected 'Producer A' in TIPL, got {metadata['TIPL']}"
        assert (
            "Engineer B" in metadata["TIPL"]
        ), f"Expected 'Engineer B' in TIPL, got {metadata['TIPL']}"

    def test_extract_metadata_invalid_file(self, tmp_path):
        """extract_metadata must return an empty dict for unparsable files."""
        file_path = tmp_path / "junk.mp3"
        file_path.write_bytes(b"Not an MP3 file content.")

        service = MetadataService()
        metadata = service.extract_metadata(str(file_path))

        assert isinstance(metadata, dict), f"Expected dict, got {type(metadata)}"
        assert metadata == {}, f"Expected empty dict, got {metadata}"

    def test_extract_metadata_file_not_found(self):
        """extract_metadata must raise FileNotFoundError for nonexistent files."""
        service = MetadataService()
        with pytest.raises(FileNotFoundError):
            service.extract_metadata("ghost_file.mp3")

    def test_extract_metadata_comprehensive_skrillex(self, silence_mp3):
        """extract_metadata must handle full complexity of modern electronic music tags."""
        from mutagen.id3 import TXXX, TPUB, TCON, TLAN

        tags = ID3()
        tags.add(TPE1(encoding=3, text=["Skrillex\u0000ISOxo"]))
        tags.add(TIT2(encoding=3, text=["RATATA"]))
        tags.add(TDRC(encoding=3, text=["2023"]))
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
        tags.add(TXXX(encoding=3, desc="STATUS", text=["Released"]))
        tags.add(TXXX(encoding=3, desc="PRODUCER", text=["Skrillex|||ISOxo"]))
        tags.add(TCOM(encoding=3, text=["Sonny Moore / Julian Isorena"]))
        tags.add(TPUB(encoding=3, text=["OWSLA\u0000Atlantic"]))
        tags.add(TCON(encoding=3, text=["Electronic / Trap"]))
        tags.add(TLAN(encoding=3, text=["eng"]))
        tags.save(str(silence_mp3))

        service = MetadataService()
        metadata = service.extract_metadata(str(silence_mp3))

        assert isinstance(metadata, dict), f"Expected dict, got {type(metadata)}"
        assert metadata["TPE1"] == [
            "Skrillex",
            "ISOxo",
        ], f"Expected TPE1=['Skrillex','ISOxo'], got {metadata['TPE1']}"
        assert metadata["TIT2"] == [
            "RATATA"
        ], f"Expected TIT2=['RATATA'], got {metadata['TIT2']}"
        assert metadata["TDRC"] == [
            "2023"
        ], f"Expected TDRC=['2023'], got {metadata['TDRC']}"
        assert (
            "Skrillex" in metadata["TIPL"]
        ), f"Expected 'Skrillex' in TIPL, got {metadata['TIPL']}"
        assert (
            "ISOxo" in metadata["TIPL"]
        ), f"Expected 'ISOxo' in TIPL, got {metadata['TIPL']}"
        assert (
            "Tom Norris" in metadata["TIPL"]
        ), f"Expected 'Tom Norris' in TIPL, got {metadata['TIPL']}"
        assert metadata["TXXX:STATUS"] == [
            "Released"
        ], f"Expected TXXX:STATUS=['Released'], got {metadata['TXXX:STATUS']}"
        assert metadata["TXXX:PRODUCER"] == [
            "Skrillex",
            "ISOxo",
        ], f"Expected TXXX:PRODUCER=['Skrillex','ISOxo'], got {metadata['TXXX:PRODUCER']}"
        assert metadata["TCOM"] == [
            "Sonny Moore",
            "Julian Isorena",
        ], f"Expected TCOM=['Sonny Moore','Julian Isorena'], got {metadata['TCOM']}"
        assert metadata["TPUB"] == [
            "OWSLA",
            "Atlantic",
        ], f"Expected TPUB=['OWSLA','Atlantic'], got {metadata['TPUB']}"
        assert metadata["TCON"] == [
            "Electronic",
            "Trap",
        ], f"Expected TCON=['Electronic','Trap'], got {metadata['TCON']}"
        assert metadata["TLAN"] == [
            "eng"
        ], f"Expected TLAN=['eng'], got {metadata['TLAN']}"

    def test_extract_metadata_tagless_file(self, silence_mp3):
        """extract_metadata must handle files with no metadata headers gracefully."""
        tags = ID3(str(silence_mp3))
        tags.delete()

        service = MetadataService()
        metadata = service.extract_metadata(str(silence_mp3))

        assert isinstance(metadata, dict), f"Expected dict, got {type(metadata)}"
        # Even tagless files get virtual TLEN from stream info
        assert "TLEN" in metadata
        assert len(metadata) == 1

    def test_extract_metadata_skips_binary(self, silence_mp3):
        """APIC and other binary frames must be ignored to prevent table pollution."""
        import mutagen.id3

        tags = mutagen.id3.ID3()
        tags.add(
            mutagen.id3.APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=b"fake_image_data",
            )
        )
        tags.add(TIT2(encoding=3, text=["Clean Title"]))
        tags.save(str(silence_mp3))

        service = MetadataService()
        metadata = service.extract_metadata(str(silence_mp3))

        assert (
            "APIC" not in metadata
        ), f"Expected 'APIC' absent from metadata keys, got {list(metadata.keys())}"
        assert (
            "TIT2" in metadata
        ), f"Expected 'TIT2' in metadata keys, got {list(metadata.keys())}"
        assert metadata["TIT2"] == [
            "Clean Title"
        ], f"Expected TIT2=['Clean Title'], got {metadata['TIT2']}"

    def test_extract_metadata_skips_descriptive_binary(self, silence_mp3):
        """Binary frames with descriptors (e.g., APIC:Cover) must still be skipped if the base ID is in config."""
        import mutagen.id3

        tags = mutagen.id3.ID3()
        # Add APIC with a description
        tags.add(
            mutagen.id3.APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=b"fake_image_data",
            )
        )
        tags.save(str(silence_mp3))

        service = MetadataService()
        metadata = service.extract_metadata(str(silence_mp3))

        # We must check all keys because Mutagen might name it APIC:Cover
        apic_keys = [k for k in metadata.keys() if k.startswith("APIC")]
        assert (
            not apic_keys
        ), f"Expected all APIC variants to be skipped, got {apic_keys}"


class TestMetadataServiceCompare:
    def test_compare_songs_identifies_scalar_mismatches(self):
        """compare_songs must detect differences in title, year, bpm, isrc, and notes."""
        from src.models.domain import Song

        def _s(title, year=2024, bpm=120, isrc="ISRC1", notes="N1"):
            return Song(
                media_name=title,
                year=year,
                bpm=bpm,
                isrc=isrc,
                notes=notes,
                source_path="path",
                duration_s=1.0,
                processing_status=1,
                credits=[],
                tags=[],
                albums=[],
                publishers=[],
            )

        service = MetadataService()

        # Test Title mismatch
        res = service.compare_songs(_s("A"), _s("B"))
        assert not res["in_sync"]
        assert "title" in res["mismatches"]

        # Test Year mismatch
        res = service.compare_songs(_s("A", year=2020), _s("A", year=2021))
        assert "year" in res["mismatches"]

        # Test BPM mismatch
        res = service.compare_songs(_s("A", bpm=120), _s("A", bpm=128))
        assert "bpm" in res["mismatches"]

        # Test Notes mismatch (Bugfix verification)
        res = service.compare_songs(_s("A", notes="Fine"), _s("A", notes="Corrupt"))
        assert "notes" in res["mismatches"]

    def test_compare_songs_identifies_album_mismatches(self):
        """compare_songs must detect differences in album title, track, and disc."""
        from src.models.domain import Song, SongAlbum

        def _s(album, track=1, disc=1):
            return Song(
                media_name="T",
                year=2024,
                bpm=120,
                source_path="path",
                duration_s=1.0,
                processing_status=1,
                credits=[],
                tags=[],
                publishers=[],
                albums=[
                    SongAlbum(album_title=album, track_number=track, disc_number=disc)
                ],
            )

        service = MetadataService()

        # Test Album mismatch
        res = service.compare_songs(_s("Album A"), _s("Album B"))
        assert "album_title" in res["mismatches"]

        # Test Disc mismatch (Bugfix verification)
        res = service.compare_songs(_s("A", disc=1), _s("A", disc=2))
        assert "disc" in res["mismatches"]
