import re
from pathlib import Path
from typing import Dict, List, Any
import mutagen
from mutagen.id3 import ID3

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


class MetadataService:
    """Service for extracting high-fidelity metadata from audio files."""

    def __init__(self):
        """Initializes the pure reading service."""
        pass

    def extract_metadata(self, file_path: str) -> Dict[str, List[str]]:
        """Reads an audio file and returns a raw dictionary of all found tags."""
        logger.info(
            f"[MetadataService] Entry: extract_metadata(file_path='{file_path}')"
        )
        path = Path(file_path)
        if not path.exists():
            logger.error(f"[MetadataService] File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Source tags (ID3 or EasyID3)
            try:
                audio = mutagen.File(file_path)
                tags = getattr(audio, "tags", None)
                if tags is None or (isinstance(tags, ID3) and len(tags) == 0):
                    tags = mutagen.easyid3.EasyID3(file_path)
            except Exception:
                tags = {}

            metadata = self._read_tags(tags)
            logger.info(
                f"[MetadataService] Exit: extract_metadata - Found {len(metadata)} tags"
            )
            return metadata

        except Exception as e:
            logger.error(
                f"[MetadataService] Exit: Error reading tags from {file_path}: {e}"
            )
            return {}

    def _read_tags(self, tags: Any) -> Dict[str, List[str]]:
        """Extracts and cleans all tags from mutagen into a clean list-based dictionary."""
        metadata = {}

        tag_items = tags.items() if hasattr(tags, "items") else []

        for tag_id, value in tag_items:
            # Data Fidelity: Extract values from lists and complex mutagen objects
            extracted = []
            if hasattr(value, "people"):
                # Handle TIPL/TMCL (Involved People List)
                extracted = [p[1] for p in value.people if len(p) > 1]
            else:
                raw_list = value if isinstance(value, (list, tuple)) else [value]
                for item in raw_list:
                    # Clean the value and split by common delimiters
                    val_str = str(item).strip()
                    # Split by common delimiters: \u0000, |||,  /
                    parts = re.split(r"\u0000|\|\|\|| / ", val_str)
                    extracted.extend([p.strip() for p in parts if p.strip()])

            if extracted:
                # Store by the raw tag ID (e.g. TPE1, TXXX:STATUS), deduplicated
                metadata[tag_id] = list(dict.fromkeys(extracted))

        return metadata
