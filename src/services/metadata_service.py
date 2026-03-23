import re
from pathlib import Path
from typing import Dict, List, Any
import mutagen
import mutagen.easyid3

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

        # 3. Clean and map tags
        metadata = self._read_tags(tags)

        # 4. Data Fidelity: Always use stream info for duration (Virtual TLEN)
        if duration_s > 0:
            metadata["TLEN"] = [str(duration_s)]

        logger.info(
            f"[MetadataService] Exit: extract_metadata - Found {len(metadata)} tags (including virtual TLEN)"
        )
        return metadata

    def _read_tags(self, tags: Any) -> Dict[str, List[str]]:
        """Extracts and cleans all tags from mutagen into a clean list-based dictionary."""
        logger.debug("[MetadataService] Entry: _read_tags")
        metadata = {}

        tag_items = tags.items() if hasattr(tags, "items") else []

        for tag_id, value in tag_items:
            # Data Fidelity: Skip binary/non-textual frames (APIC=Picture, GEOB=Object, PRIV=Private)
            if tag_id.startswith(("APIC", "GEOB", "PRIV")):
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
