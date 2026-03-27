import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import ValidationError
from src.models.domain import Song, SongCredit, SongAlbum, Tag, Publisher, AlbumCredit
from src.services.logger import logger
from src.engine.config import COMMA_SPLIT_FIELDS


class MetadataParser:
    """Parses raw metadata dictionaries into relaxed Song domain models."""

    def __init__(self, json_path: str = "json/id3_frames.json"):
        """Initializes the parser with the frame mapping configuration."""
        self.config = self._load_config(json_path)
        # Pre-process config for faster lookup
        self.field_map = {}
        self.tag_map = {}

        for tag_id, entry in self.config.items():
            if isinstance(entry, dict):
                field = entry.get("field")
                if field:
                    self.field_map[tag_id] = entry

                category = entry.get("tag_category")
                if category:
                    self.tag_map[tag_id] = entry

    def _load_config(self, json_path: str) -> Dict[str, Any]:
        """Loads the JSON configuration using utf-8-sig to handle BOM."""
        try:
            path = Path(json_path)
            if not path.exists():
                logger.warning(f"[MetadataParser] Config not found at {json_path}")
                return {}

            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[MetadataParser] Error loading config: {e}")
            return {}

    def parse(self, raw_metadata: Dict[str, List[str]], file_path: str) -> Song:
        """Translates raw tags into a Song object using the frame map."""
        logger.info(f"[MetadataParser] Entry: parse(file_path='{file_path}')")

        # Prepare the core song data
        song_data = {
            "media_name": "",
            "source_path": str(file_path),
            "duration_s": 0.0,
            "credits": [],
            "tags": [],
            "albums": [],
            "publishers": [],
            "raw_tags": {},
        }

        # Temporary buckets for list-based data to allow deduplication while preserving order
        credits_dict = {}  # role_name -> list of display_names
        tags_dict = {}  # category -> list of names
        primary_tag_categories: set = set()  # categories that already have a primary from dynamic frames
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

            field_name = entry.get("field") if isinstance(entry, dict) else None
            category = entry.get("tag_category") if isinstance(entry, dict) else None
            type_info = entry.get("type", "text") if isinstance(entry, dict) else "text"

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
                        role_name = self._get_role_name(field_name)
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

            # 4. Fallback: Create dynamic tags for unknown descriptor-based frames (e.g. TXXX:STATUS)
            if not category and (not field_name or isinstance(entry, str)):
                if ":" in tag_id:
                    # Treat as a dynamic Tag: Category is the descriptor, values are the names
                    prefix, desc = tag_id.split(":", 1)
                    # Normalize category name (e.g. FESTIVAL -> Festival)
                    cat_name = desc.capitalize()
                    for i, v in enumerate(values):
                        song_data["tags"].append(Tag(name=str(v), category=cat_name, is_primary=(i == 0)))
                        if i == 0:
                            primary_tag_categories.add(cat_name)
                elif not field_name:
                    # Genuine raw tag (no descriptor), keep in raw_tags
                    label = (
                        (entry.get("description") or tag_id)
                        if isinstance(entry, dict)
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
                song_data["tags"].append(Tag(name=name, category=category, is_primary=is_primary))

        # Move contextual fields from root to relationship-only
        track_num = song_data.pop("track_number", None)
        disc_num = song_data.pop("disc_number", None)

        # Build album credits from parsed album artists
        album_credit_models = []
        for name in dict.fromkeys(album_artists):
            album_credit_models.append(
                AlbumCredit(role_name="Album Artist", display_name=name)
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

    def _get_role_name(self, field: str) -> str:
        """Maps internal field names to human-readable Role names."""
        mapping = {
            "artist": "Performer",
            "producers": "Producer",
            "composers": "Composer",
            "lyricists": "Lyricist",
            "album_artist": "Album Artist",
            "groups": "Group",
        }
        return mapping.get(field, field.capitalize())
