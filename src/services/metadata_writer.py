from typing import Any
from pathlib import Path
from mutagen.id3 import (
    ID3,
    TXXX,
    COMM,
)
from src.models.domain import Song
from src.services.logger import logger
from src.services.metadata_frames_reader import load_id3_frames
from src.models.metadata_frames import ID3FrameConfig


class MetadataWriter:
    """Stateless service for writing Domain Model metadata back to physical ID3 tags."""

    def __init__(self):
        self.config = load_id3_frames()

        # Pre-process for config-driven inverse lookup
        self.field_to_tag = {}
        self.category_to_tag = {}
        self.role_to_tag = {}

        if self.config:
            for tag_id, entry in self.config.items():
                if isinstance(entry, ID3FrameConfig):
                    if entry.skip_write:
                        continue
                    if entry.field:
                        self.field_to_tag[entry.field] = tag_id
                    if entry.role:
                        self.role_to_tag[entry.role] = tag_id
                    if entry.tag_category:
                        self.category_to_tag[entry.tag_category] = tag_id

    def write_metadata(self, song: Song) -> None:
        """
        Writes the current state of a Song object to its physical file.
        Uses ID3v2.4 standards with true multi-value support.
        """
        path = Path(song.source_path)
        if not path.exists():
            logger.error(f"[MetadataWriter] File not found: {path}")
            raise FileNotFoundError(f"Audio file not found at {path}")

        if path.suffix.lower() != ".mp3":
            logger.warning(f"[MetadataWriter] Skipping non-MP3 file: {path}")
            return

        logger.info(
            f"[MetadataWriter] Entry: write_metadata(id={song.id}, path='{path}')"
        )

        try:
            # Open existing tags or create new container — preserves frames we don't own (APIC, etc.)
            try:
                tags = ID3(str(path))
            except Exception:
                tags = ID3()

            # Tags this pass actually writes. Anything owned (in the config maps
            # below) but not written here means the source value was removed —
            # we clear those frames. Unmapped/dynamic TXXX frames (custom role
            # or tag-category names) are never auto-cleared: we can't tell
            # "removed" from "was never ours" for those, so touching them risks
            # deleting data we don't understand.
            written_tag_ids = set()

            # 1. Map Scalars via Config Field Map
            for field, tag_id in self.field_to_tag.items():
                val = getattr(song, field, None)
                if val is not None:
                    self._apply_frame(tags, tag_id, val)
                    written_tag_ids.add(tag_id)

            # Map Notes to Common Comments (COMM)
            if song.notes:
                self._apply_frame(tags, "COMM", song.notes)
                written_tag_ids.add("COMM")

            # 2. Credits (Config-driven Role Mapping)
            credits_by_role = {}
            for credit in song.credits:
                credits_by_role.setdefault(credit.role_name, []).append(
                    credit.display_name
                )

            for role, names in credits_by_role.items():
                unique_names = list(dict.fromkeys(names))
                tag_id = self.role_to_tag.get(role)

                if tag_id:
                    self._apply_frame(tags, tag_id, unique_names)
                    written_tag_ids.add(tag_id)
                else:
                    # Fallback to TXXX:RoleName for unmapped credits
                    tags.add(TXXX(encoding=3, desc=role, text=unique_names))

            # 3. Tags (Config-driven Category Mapping)
            tags_by_cat = {}
            for t in song.tags:
                cat = t.category or "Tag"
                tags_by_cat.setdefault(cat, []).append(t.name)

            for cat, names in tags_by_cat.items():
                unique_names = list(dict.fromkeys(names))
                tag_id = self.category_to_tag.get(cat)
                if tag_id:
                    self._apply_frame(tags, tag_id, unique_names)
                    written_tag_ids.add(tag_id)
                else:
                    tags.add(TXXX(encoding=3, desc=cat, text=unique_names))

            # 4. Albums / Media Meta
            # ID3 holds a single album, so write the primary one (fall back to
            # first if none is flagged). albums[0] is not primary-aware.
            if song.albums:
                album = next((a for a in song.albums if a.is_primary), song.albums[0])
                self._apply_frame(tags, "TALB", album.album_title)
                written_tag_ids.add("TALB")
                if album.track_number:
                    self._apply_frame(tags, "TRCK", str(album.track_number))
                    written_tag_ids.add("TRCK")
                if album.disc_number:
                    self._apply_frame(tags, "TPOS", str(album.disc_number))
                    written_tag_ids.add("TPOS")

                # Album Artist (Config-driven if possible, else TPE2)
                album_artists = list(
                    dict.fromkeys(
                        [
                            c.display_name
                            for c in album.credits
                            if c.role_name == "Performer"
                        ]
                    )
                )
                if album_artists:
                    self._apply_frame(tags, "TPE2", album_artists)
                    written_tag_ids.add("TPE2")

            # 5. Publishers
            if song.publishers:
                pub_names = list(dict.fromkeys([p.name for p in song.publishers]))
                self._apply_frame(tags, "TPUB", pub_names)
                written_tag_ids.add("TPUB")

            # 6. Clear owned frames whose source value is now absent
            owned_tag_ids = (
                set(self.field_to_tag.values())
                | set(self.role_to_tag.values())
                | set(self.category_to_tag.values())
                | {"COMM"}
            )
            for tag_id in owned_tag_ids - written_tag_ids:
                self._delete_frame(tags, tag_id)

            # FORCE ID3v2.4 — update_to_v24 converts any v2.3 frame aliases (TP1→TPE1 etc)
            tags.update_to_v24()
            tags.save(str(path), v2_version=4)
            logger.info(
                f"[MetadataWriter] Exit: Successfully saved tags (v2.4) to {path}"
            )

        except Exception as e:
            logger.error(f"[MetadataWriter] Critical error writing to {path}: {e}")
            raise

    def _delete_frame(self, tags: ID3, tag_id: str) -> None:
        """Removes an owned frame whose source value is now absent, mirroring _apply_frame's key logic."""
        if ":" in tag_id:
            prefix, desc = tag_id.split(":", 1)
            if prefix == "TXXX":
                key = f"TXXX:{desc}"
                if key in tags:
                    del tags[key]
            return

        if tag_id == "COMM":
            key = "COMM::eng"
            if key in tags:
                del tags[key]
            return

        if tag_id in tags:
            del tags[tag_id]

    def _apply_frame(self, tags: ID3, tag_id: str, value: Any) -> None:
        """Applies a specific frame, handling list vs scalar and frame type dispatch."""
        if not isinstance(value, list):
            value = [str(value)]

        # Handle TXXX descriptors (e.g. TXXX:STATUS)
        if ":" in tag_id:
            prefix, desc = tag_id.split(":", 1)
            if prefix == "TXXX":
                # Check for existing frame with same description to overwrite
                tags.add(TXXX(encoding=3, desc=desc, text=value))
            return

        # Special Case: COMM (Comments) - Needs lang and description
        if tag_id == "COMM":
            tags.add(COMM(encoding=3, lang="eng", desc="", text=value))
            return

        # Frame Type Dispatch via dynamic mutagen lookup
        import mutagen.id3

        cls = getattr(mutagen.id3, tag_id, None)
        if cls:
            # Multi-string support via list
            tags[tag_id] = cls(encoding=3, text=value)
        else:
            # Fallback to TXXX if unknown mapping to prevent data loss
            tags.add(TXXX(encoding=3, desc=tag_id, text=value))
