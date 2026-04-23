import unicodedata
import json
import re
import shutil
from pathlib import Path
from src.models.domain import Song
from src.services.logger import logger


class FilingService:
    """Handles physiological file routing, renaming, and ASCII sanitization for the library."""

    def __init__(self, rules_path: Path):
        self._rules_path = rules_path
        self._rules = self._load_rules()

    def _load_rules(self) -> dict:
        """Load routing rules from the specified JSON file."""
        if not self._rules_path.exists():
            logger.warning(
                f"[FilingService] Rules file not found at {self._rules_path}. Using fallback."
            )
            return {
                "routing_rules": [],
                "default_rule": "{genre}/{year}/{artist} - {title}",
            }

        try:
            with open(self._rules_path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[FilingService] Error loading rules: {e}")
            return {
                "routing_rules": [],
                "default_rule": "{genre}/{year}/{artist} - {title}",
            }

    def evaluate_routing(self, song: Song) -> Path:
        """
        Calculates the target relative path for a song based on rules.json.
        Applies ASCII-only sanitization for the physical filename structure.
        """
        logger.debug(f"[FilingService] -> evaluate_routing(song_id={song.id})")

        # 1. Identify primary genre for matching (case-insensitive)
        genre_tags = [
            t for t in song.tags if t.category and t.category.lower() == "genre"
        ]
        primary_genre_tag = next((t for t in genre_tags if t.is_primary), None)
        if not primary_genre_tag and genre_tags:
            primary_genre_tag = genre_tags[0]

        if not primary_genre_tag:
            raise ValueError(
                f"Song {song.id} is missing a Primary Genre (required for routing)"
            )

        genre_name = primary_genre_tag.name
        primary_genre = genre_name.lower()

        # 2. Extract and format placeholders
        # {artist} = comma-delimited performers
        performers = [
            c.display_name for c in song.credits if c.role_name == "Performer"
        ]
        if not performers:
            raise ValueError(
                f"Song {song.id} is missing Performer credits (required for routing)"
            )

        artist_str = ", ".join(performers)

        if not song.media_name:
            raise ValueError(
                f"Song {song.id} is missing a Title/MediaName (required for routing)"
            )

        if not song.year:
            raise ValueError(
                f"Song {song.id} is missing a Recording Year (required for routing)"
            )

        placeholders = {
            "artist": self._sanitize_for_filesystem(artist_str),
            "title": self._sanitize_for_filesystem(song.media_name),
            "year": self._sanitize_for_filesystem(str(song.year)),
            "genre": self._sanitize_for_filesystem(genre_name),
        }

        # 3. Find matching rule
        rule_path_template = None
        for rule in self._rules.get("routing_rules", []):
            match_genres = [g.lower() for g in rule.get("match_genres", [])]
            if primary_genre in match_genres:
                rule_path_template = rule.get("target_path")
                break

        if not rule_path_template:
            rule_path_template = self._rules.get("default_rule")

        if not rule_path_template:
            logger.warning(
                f"[FilingService] <- evaluate_routing() FAILURE: No rule matches genre '{genre_name}' and no default_rule defined."
            )
            raise ValueError(
                f"No filing rule exists for genre '{genre_name}' and no default_rule found. Add it to rules.json."
            )

        # 4. Interpolate the sanitized components into the structural directory rule
        raw_path = rule_path_template.format(**placeholders)

        # 5. Clean up structural borders (stripping rogue spaces/dots from folder names)
        components = [c.strip(". ") for c in raw_path.replace("\\", "/").split("/")]
        sanitized_path = "/".join(components)

        # 6. Preserve extension from source
        orig_ext = Path(song.source_path or "").suffix or ".mp3"
        final_path = Path(sanitized_path).with_suffix(orig_ext)

        logger.debug(f"[FilingService] <- evaluate_routing() target: {final_path}")
        return final_path

    def _sanitize_for_filesystem(self, path_str: str) -> str:
        """
        Transliterates UTF-8 characters to ASCII and replaces illegal filesystem characters.
        Preserves path delimiters (slashes) to maintain directory structure.
        """
        # 1. Manual Transliteration for Slavic chars that NFKD doesn't handle as combinations
        # Đ -> Dj, đ -> dj, Ć -> C, ć -> c, etc.
        mapping = {
            "Đ": "Dj",
            "đ": "dj",
            "Ć": "C",
            "ć": "c",
            "Č": "C",
            "č": "c",
            "Š": "S",
            "š": "s",
            "Ž": "Z",
            "ž": "z",
        }
        for char, replacement in mapping.items():
            path_str = path_str.replace(char, replacement)

        # 2. Transliterate (Normalize NFKD to decompose, then encode ascii 'ignore')
        # This handles accented chars like 'ö', 'à'
        normalized = unicodedata.normalize("NFKD", path_str)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")

        # 3. Path-Illegal Character Cleanup
        # We replace slashes, colons, and illegal characters with _
        safe = re.sub(r'[\\/*?"<>|:]', "_", ascii_only)

        # 4. Collapse multiple spaces
        safe = re.sub(r"  +", " ", safe)

        return safe.strip(". ")

    def copy_to_library(self, song: Song, library_root: Path) -> Path:
        """
        Copies the physical file to the organized library root.
        This is Stage 1 of a safe filing transaction.
        The source file is NOT removed until the database update is confirmed.
        """
        target_relative = self.evaluate_routing(song)
        target_absolute = library_root / target_relative

        source_path = Path(song.source_path)
        if not source_path.exists():
            logger.error(f"[FilingService] Source file not found: {source_path}")
            raise FileNotFoundError(f"Source file not found: {source_path}")

        if target_absolute.exists():
            try:
                if (
                    source_path.resolve() == target_absolute.resolve()
                    or source_path.samefile(target_absolute)
                ):
                    logger.info(
                        f"[FilingService] File already natively exists at perfect target path, bypassing physical copy: {target_absolute}"
                    )
                    return target_absolute
            except Exception:
                pass
            raise FileExistsError(
                f"Target path already exists in library: {target_absolute}"
            )

        # Ensure target directory exists
        if not target_absolute.parent.exists():
            target_absolute.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"[FilingService] Copying: {source_path} -> {target_absolute}")

        shutil.copy2(str(source_path), str(target_absolute))
        return target_absolute

    def move_to_library(self, song: Song, library_root: Path) -> Path:
        """Organizes a file into the library and removes the old source."""
        source_path = Path(song.source_path)
        target_path = self.copy_to_library(song, library_root)

        # Safe comparison: samefile() handles different path formats pointing to same inode
        is_same = False
        try:
            if source_path.exists() and target_path.exists():
                is_same = source_path.samefile(target_path)
        except Exception:
            pass

        if source_path.exists() and not is_same:
            source_path.unlink()
            logger.debug(f"[FilingService] Unlinked old source: {source_path}")

        return target_path
