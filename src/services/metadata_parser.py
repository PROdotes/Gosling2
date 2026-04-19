import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import ValidationError
from src.models.domain import Song, SongCredit, SongAlbum, Tag, Publisher, AlbumCredit
from src.models.metadata_frames import ID3FrameConfig
from src.services.logger import logger
from src.services.metadata_frames_reader import load_id3_frames, load_tag_categories
from src.engine.config import COMMA_SPLIT_FIELDS, SONG_DEFAULT_YEAR, ProcessingStatus


class MetadataParser:
    """Parses raw metadata dictionaries into relaxed Song domain models."""

    def __init__(self, json_path: str = "json/id3_frames.json"):
        """Initializes the parser with the frame mapping configuration."""
        self.config = load_id3_frames(json_path)
        # Pre-process config for faster lookup
        self.field_map = {}
        self.tag_map = {}
        self.role_map = {}  # field_name -> role_name
        self.tag_categories = set(load_tag_categories())
        assert self.config is not None, "Metadata configuration failed to load"
        for tag_id, entry in self.config.items():
            if isinstance(entry, ID3FrameConfig):
                if entry.field:
                    self.field_map[tag_id] = entry
                    if entry.role:
                        self.role_map[entry.field] = entry.role
                if entry.tag_category:
                    self.tag_map[tag_id] = entry

    def parse(self, raw_metadata: Dict[str, List[str]], file_path: str) -> Song:
        """Translates raw tags into a Song object using the frame map."""
        logger.info(f"[MetadataParser] Entry: parse(file_path='{file_path}')")

        # Prepare the core song data
        song_data = {
            "media_name": "",
            "source_path": str(file_path),
            "duration_s": 0.0,
            "processing_status": ProcessingStatus.PENDING_ENRICHMENT,
            "credits": [],
            "tags": [],
            "albums": [],
            "publishers": [],
            "raw_tags": {},
        }

        # Temporary buckets for list-based data to allow deduplication while preserving order
        credits_dict = {}  # role_name -> list of display_names
        tags_dict = {}  # category -> list of names
        primary_tag_categories: set = (
            set()
        )  # categories that already have a primary from dynamic frames
        album_titles = []
        publisher_names = []
        album_artists = []

        for tag_id, values in raw_metadata.items():
            # Sub-tag check (e.g. TXXX:STATUS)
            entry = self.config.get(tag_id)

            if not entry:
                logger.debug(
                    f"[MetadataParser] Tag ID {tag_id} not in config, will treat as raw tag."
                )
                # We don't continue here anymore; we let it fall through to Step 4.
                pass

            field_name = entry.field if isinstance(entry, ID3FrameConfig) else None
            category = entry.tag_category if isinstance(entry, ID3FrameConfig) else None
            type_info = entry.type if isinstance(entry, ID3FrameConfig) else "text"

            if isinstance(entry, str):
                logger.debug(
                    f"[MetadataParser] Entry for {tag_id} is string label: {entry}"
                )
                # If it's a sub-tag (e.g. TXXX:DESC), we let it fall through to the dynamic tag logic (Step 4)
                # If it's a simple tag (no colon), we'll catch it in the fallback as a raw_tag.
                pass

            if field_name and values:
                # 1. Routing to core Song fields (Integer/Text/Float)
                if type_info == "integer":
                    raw_val = values[0]
                    if field_name == "year" and "-" in str(raw_val):
                        raw_val = str(raw_val).split("-")[0]

                    val_int = self._to_int(raw_val)
                    if val_int is not None:
                        song_data[field_name] = val_int

                elif type_info == "float":
                    try:
                        song_data[field_name] = float(values[0])
                    except (ValueError, TypeError):
                        pass

                elif type_info == "text":
                    song_data[field_name] = str(values[0])

                # 2. Routing to Collections (Credits, Publishers, Albums)
                elif type_info == "list":
                    if field_name == "publisher":
                        publisher_names.extend([str(v) for v in values])
                    elif field_name == "album_title":
                        album_titles.extend([str(v) for v in values])
                    elif field_name == "album_artist":
                        album_artists.extend([str(v) for v in values])
                    else:
                        # Priority: 1. Config 'role' attribute, 2. Existing role_map lookup, 3. Capitalized field
                        role_name = (
                            entry.role
                            if isinstance(entry, ID3FrameConfig) and entry.role
                            else self.role_map.get(field_name, field_name.capitalize())
                        )
                        if field_name in COMMA_SPLIT_FIELDS:
                            split_values = [
                                part.strip()
                                for v in values
                                for part in str(v).split(",")
                                if part.strip()
                            ]
                            credits_dict.setdefault(role_name, []).extend(split_values)
                        else:
                            credits_dict.setdefault(role_name, []).extend(
                                [str(v) for v in values]
                            )

            # 3. Routing to Tags
            if category:
                tags_dict.setdefault(category, []).extend([str(v) for v in values])

            # 4. Fallback: promote unknown colon-frames to tags only if their descriptor
            # is a registered category. Everything else goes to raw_tags.
            # To add a new custom tag category, add it to tag_categories in id3_frames.json.
            if not category and not field_name:
                if ":" in tag_id:
                    _, desc = tag_id.split(":", 1)
                    cat_name = desc.capitalize()
                    if cat_name in self.tag_categories:
                        for i, v in enumerate(values):
                            song_data["tags"].append(
                                Tag(name=str(v), category=cat_name, is_primary=(i == 0))
                            )
                            if i == 0:
                                primary_tag_categories.add(cat_name)
                    else:
                        song_data["raw_tags"][tag_id] = values
                else:
                    label = (
                        entry.description
                        if isinstance(entry, ID3FrameConfig)
                        else (entry or tag_id)
                    )
                    song_data["raw_tags"][label] = values

        # Build objects from buckets using dict.fromkeys to deduplicate while preserving "First Seen" order
        for role, names in credits_dict.items():
            for name in dict.fromkeys(names):
                song_data["credits"].append(
                    SongCredit(role_name=role, display_name=name)
                )

        for category, names in tags_dict.items():
            already_has_primary = category in primary_tag_categories
            for i, name in enumerate(dict.fromkeys(names)):
                is_primary = (i == 0) and not already_has_primary
                song_data["tags"].append(
                    Tag(name=name, category=category, is_primary=is_primary)
                )

        # Move contextual fields from root to relationship-only
        track_num = song_data.pop("track_number", None)
        disc_num = song_data.pop("disc_number", None)

        # Build album credits from parsed album artists
        album_credit_models = []
        for name in dict.fromkeys(album_artists):
            album_credit_models.append(
                AlbumCredit(role_name="Performer", display_name=name)
            )

        for album in dict.fromkeys(album_titles):
            song_data["albums"].append(
                SongAlbum(
                    album_title=album,
                    track_number=track_num,
                    disc_number=disc_num,
                    album_publishers=[],
                    credits=album_credit_models,
                )
            )

        for pub_name in dict.fromkeys(publisher_names):
            song_data["publishers"].append(Publisher(name=pub_name))

        if not song_data["media_name"]:
            stem = Path(file_path).stem
            song_data["media_name"] = re.sub(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_",
                "",
                stem,
            )

        if "year" not in song_data:
            song_data["year"] = SONG_DEFAULT_YEAR

        try:
            song = Song(**song_data)
            logger.info(
                f"[MetadataParser] Exit: parse - Created Song with {len(song.credits)} credits and {len(song.tags)} tags"
            )
            return song
        except ValidationError as e:
            logger.error(f"[MetadataParser] Validation error creating Song: {e}")
            raise ValueError(f"Failed to parse metadata into Song model: {e}")

    def _to_int(self, val: Any) -> Optional[int]:
        """Safely converts a value to an integer, discarding junk."""
        try:
            # Handle cases like "2023/2024" or "128 BPM"
            clean = "".join(filter(str.isdigit, str(val)))
            return int(clean) if clean else None
        except (ValueError, TypeError):
            return None
