"""Metadata extraction service"""
from typing import Optional
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError
from ...data.models.song import Song


class MetadataService:
    """Service for extracting metadata from audio files"""

    @staticmethod
    def extract_from_mp3(path: str, file_id: Optional[int] = None) -> Song:
        """
        Extract metadata from an MP3 file and return a Song object.
        Handles missing tags gracefully.
        """
        try:
            audio = MP3(path)
        except Exception as e:
            raise ValueError(f"Unable to read MP3 file: {path}") from e

        duration = audio.info.length if audio.info else None

        # Try reading existing ID3 tags
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = {}

        # Helper to read text frames as list[str]
        def get_text_list(frame_id):
            if frame_id not in tags:
                return []
            frame = tags.getall(frame_id)
            values = []
            for f in frame:
                if hasattr(f, "text"):
                    for item in f.text:
                        if item:
                            values.append(str(item).strip())
            return values

        # Extract title
        title = None
        if "TIT2" in tags:
            title_items = tags.getall("TIT2")[0].text
            title = title_items[0].strip() if title_items else None

        # Extract contributors
        performers = get_text_list("TPE1")
        composers = get_text_list("TCOM")
        lyricists = get_text_list("TOLY") or get_text_list("TEXT")
        groups = get_text_list("TIT1")

        # Extract BPM
        bpm_list = get_text_list("TBPM")
        bpm = int(bpm_list[0]) if bpm_list else None

        # Extract producers
        producers = []
        if "TIPL" in tags:
            for p in tags.getall("TIPL"):
                if hasattr(p, "people"):
                    for role, name in p.people:
                        if role.lower() == "producer":
                            producers.append(name.strip())

        if "TXXX:PRODUCER" in tags:
            producers.extend(get_text_list("TXXX:PRODUCER"))

        return Song(
            file_id=file_id,
            path=path,
            title=title,
            duration=duration,
            bpm=bpm,
            performers=list(dict.fromkeys(performers)),
            composers=list(dict.fromkeys(composers)),
            lyricists=list(dict.fromkeys(lyricists)),
            producers=list(dict.fromkeys(producers)),
            groups=list(dict.fromkeys(groups)),
        )

