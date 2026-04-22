import re
from pathlib import Path
from typing import Dict, List, Any
import mutagen
import mutagen.easyid3
from src.models.domain import Song

try:
    from mutagen.id3 import (
        ID3NoHeaderError,
        HeaderNotFoundError,
        ID3HeaderError,
        ID3TagError,
    )
except ImportError:
    # Fallback for different mutagen versions
    ID3NoHeaderError = Exception
    HeaderNotFoundError = Exception
    ID3HeaderError = Exception
    ID3TagError = Exception

from src.services.logger import logger
from src.services.metadata_frames_reader import load_id3_frames
from src.models.metadata_frames import ID3FrameConfig


class MetadataService:
    """Service for extracting high-fidelity metadata from audio files."""

    def __init__(self, json_path: str = "json/id3_frames.json"):
        """Initializes the pure reading service with frame configuration."""
        self.config = load_id3_frames(json_path)

    def extract_metadata(self, file_path: str) -> Dict[str, List[str]]:
        """Reads an audio file and returns a raw dictionary of all found tags."""
        logger.info(
            f"[MetadataService] Entry: extract_metadata(file_path='{file_path}')"
        )
        path = Path(file_path)
        if not path.exists():
            logger.error(f"[MetadataService] File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        audio = None
        duration_s: float = 0.0
        tags = {}

        try:
            # 1. Try to read the audio file structure (Stream Info)
            audio = mutagen.File(file_path)
            if audio is not None and hasattr(audio, "info") and audio.info:
                duration_s = getattr(audio.info, "length", 0.0)

            # 2. Try to extract tags (Pure ID3/Tags only)
            tags = getattr(audio, "tags", {}) if audio is not None else {}

        except (ID3NoHeaderError, HeaderNotFoundError, ID3HeaderError, ID3TagError):
            # If tags are missing, it might raise, but we still have 'tags = {}'
            pass
        except Exception as e:
            logger.error(f"[MetadataService] Mutagen error reading {file_path}: {e}")
        finally:
            # SCAR: Windows File Locking. Explicitly release handle.
            if audio is not None:
                try:
                    audio.close()
                except Exception:
                    pass

        # 3. Clean and map tags
        metadata = self._read_tags(tags)

        # 4. Data Fidelity: Always use stream info for duration (Virtual TLEN)
        if duration_s > 0:
            metadata["TLEN"] = [str(duration_s)]

        logger.info(
            f"[MetadataService] Exit: extract_metadata - Found {len(metadata)} tags (including virtual TLEN)"
        )
        return metadata

    def compare_songs(self, db_song: Song, file_song: Song) -> dict:
        """
        Compares two Song objects field by field.
        Returns {in_sync: bool, mismatches: [field_name, ...]}
        """
        mismatches = []

        def _check_scalar(label: str, db_val, file_val):
            if str(db_val or "") != str(file_val or ""):
                mismatches.append(label)

        def _check_list(label: str, db_list: list, file_list: list):
            if sorted(db_list) != sorted(file_list):
                mismatches.append(label)

        def _names_by_role(song: Song, role: str) -> list:
            return sorted(
                set(c.display_name for c in song.credits if c.role_name == role)
            )

        def _names_by_cat(song: Song, cat: str) -> list:
            return sorted(set(t.name for t in song.tags if t.category == cat))

        # Scalars
        _check_scalar("title", db_song.media_name, file_song.media_name)
        _check_scalar("year", db_song.year, file_song.year)
        _check_scalar("bpm", db_song.bpm, file_song.bpm)
        _check_scalar("isrc", db_song.isrc, file_song.isrc)
        _check_scalar("notes", db_song.notes, file_song.notes)
        _check_scalar("duration", db_song.duration_s, file_song.duration_s)

        # Credits by role
        all_roles = set(c.role_name for c in db_song.credits if c.role_name) | set(
            c.role_name for c in file_song.credits if c.role_name
        )
        for role in all_roles:
            if not role:
                continue
            _check_list(
                f"credit:{role}",
                _names_by_role(db_song, role),
                _names_by_role(file_song, role),
            )

        # Tags by category
        all_cats = set(t.category for t in db_song.tags if t.category) | set(
            t.category for t in file_song.tags if t.category
        )
        for cat in all_cats:
            if not cat:
                continue
            _check_list(
                f"tag:{cat}", _names_by_cat(db_song, cat), _names_by_cat(file_song, cat)
            )

        # Publishers
        _check_list(
            "publishers",
            sorted(set(p.name for p in db_song.publishers)),
            sorted(set(p.name for p in file_song.publishers)),
        )

        # Album
        db_album = db_song.albums[0] if db_song.albums else None
        file_album = file_song.albums[0] if file_song.albums else None
        _check_scalar(
            "album_title",
            db_album.album_title if db_album else None,
            file_album.album_title if file_album else None,
        )
        _check_scalar(
            "track",
            db_album.track_number if db_album else None,
            file_album.track_number if file_album else None,
        )
        _check_scalar(
            "disc",
            db_album.disc_number if db_album else None,
            file_album.disc_number if file_album else None,
        )

        return {"in_sync": len(mismatches) == 0, "mismatches": mismatches}

    def filter_sync_mismatches(self, db_song: Song, mismatches: list) -> list:
        """
        Filters raw compare_songs mismatches to only those relevant to DB state.
        Removes tag:* mismatches for categories that exist only in the file, not in the DB.
        """
        db_tag_categories = set(t.category for t in db_song.tags)
        return [
            m
            for m in mismatches
            if not m.startswith("tag:") or m[4:] in db_tag_categories
        ]

    def _read_tags(self, tags: Any) -> Dict[str, List[str]]:
        """Extracts and cleans all tags from mutagen into a clean list-based dictionary."""
        logger.debug("[MetadataService] Entry: _read_tags")
        metadata = {}

        tag_items = tags.items() if hasattr(tags, "items") else []

        for tag_id, value in tag_items:
            # Data Fidelity: Honor skip_read flag from config (including prefix matching for descriptive tags)
            base_tag = tag_id.split(":", 1)[0] if ":" in tag_id else tag_id
            entry = self.config.get(tag_id) or self.config.get(base_tag)

            if isinstance(entry, ID3FrameConfig) and entry.skip_read:
                continue

            # Data Fidelity: Extract values from lists and complex mutagen objects
            extracted = []
            people = getattr(value, "people", None)
            if people:
                # Handle TIPL/TMCL (Involved People List)
                extracted = [p[1] for p in people if len(p) > 1]
            else:
                raw_list = value if isinstance(value, (list, tuple)) else [value]
                for item in raw_list:
                    # Clean the value and split by common delimiters
                    val_str = str(item).strip()
                    # Data Fidelity: Split by 'hard' nulls and established safe delimiters.
                    # We avoid splitting by single ';' to protect song titles.
                    parts = re.split(r"\u0000|\|\|\|| / ", val_str)
                    extracted.extend([p.strip() for p in parts if p.strip()])

            if extracted:
                # Store by the raw tag ID (e.g. TPE1, TXXX:STATUS), deduplicated
                metadata[tag_id] = list(dict.fromkeys(extracted))

        logger.debug(
            f"[MetadataService] Exit: _read_tags - Extracted {len(metadata)} frames"
        )
        return metadata
