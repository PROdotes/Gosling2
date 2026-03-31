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
            "artist": artist_str,
            "title": song.media_name,
            "year": str(song.year),
            "genre": genre_name,
        }

        # 3. Find matching rule
        rule_path_template = None
        for rule in self._rules.get("routing_rules", []):
            match_genres = [g.lower() for g in rule.get("match_genres", [])]
            if primary_genre in match_genres:
                rule_path_template = rule.get("target_path")
                break

        if not rule_path_template:
            logger.warning(
                f"[FilingService] <- evaluate_routing() FAILURE: No rule matches genre '{genre_name}'"
            )
            raise ValueError(
                f"No filing rule exists for genre '{genre_name}'. Add it to rules.json."
            )

        # 4. Interpolate and sanitize
        raw_path = rule_path_template.format(**placeholders)

        # 5. Physical Filename Sanitization (ASCII-only, no illegal chars)
        sanitized_path = self._sanitize_for_filesystem(raw_path)

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

        # 3. Path-Illegal Character Cleanup (except slashes)
        # We replace : * ? " < > | with _ to preserve path structure but stay safe
        # GOSLING protocol: keep spaces, they are fine in modern file systems
        safe = re.sub(r'[\\:*?"<>|]', "_", ascii_only)

        # 4. Collapse multiple spaces or dots
        safe = re.sub(r"  +", " ", safe)

        # 5. Remove leading/trailing periods or spaces from each component
        components = [c.strip(". ") for c in safe.replace("\\", "/").split("/")]
        return "/".join(components)

    def copy_to_library(self, song: Song, library_root: Path) -> Path:
        """
        Copies the physical file to the organized library root.
        This is Stage 1 of a safe filing transaction.
        The source file is NOT removed until the database update is confirmed.
        """
        target_relative = self.evaluate_routing(song)
        target_absolute = library_root / target_relative

        if target_absolute.exists():
            raise FileExistsError(
                f"Target path already exists in library: {target_absolute}"
            )

        # Ensure target directory exists
        if not target_absolute.parent.exists():
            target_absolute.parent.mkdir(parents=True, exist_ok=True)

        source_path = Path(song.source_path)
        if not source_path.exists():
            logger.error(f"[FilingService] Source file not found: {source_path}")
            raise FileNotFoundError(f"Source file not found: {source_path}")

        logger.info(f"[FilingService] Copying: {source_path} -> {target_absolute}")

        shutil.copy2(str(source_path), str(target_absolute))

        return target_absolute
