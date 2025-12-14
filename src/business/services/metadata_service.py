"""Metadata extraction service"""
from typing import Optional, List
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
        def get_text_list(frame_id: str) -> List[str]:
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

        # Helper to deduplicate lists while preserving order
        def deduplicate(items: List[str]) -> List[str]:
            return list(dict.fromkeys(items))

        # Helper to extract producers from TIPL and TXXX tags
        def get_producers() -> List[str]:
            producers = []
            
            # Extract from TIPL (Involved People List)
            if "TIPL" in tags:
                for p in tags.getall("TIPL"):
                    if hasattr(p, "people"):
                        for role, name in p.people:
                            if role.lower() == "producer":
                                producers.append(name.strip())
            
            # Extract from TXXX:PRODUCER
            if "TXXX:PRODUCER" in tags:
                producers.extend(get_text_list("TXXX:PRODUCER"))
            
            return producers

        # Extract title (use get_text_list for consistency)
        title_list = get_text_list("TIT2")
        title = title_list[0] if title_list else None

        # Extract contributors
        performers = get_text_list("TPE1")
        composers = get_text_list("TCOM")
        lyricists = get_text_list("TOLY") or get_text_list("TEXT")
        groups = get_text_list("TIT1")

        # Extract BPM
        bpm_list = get_text_list("TBPM")
        bpm = int(bpm_list[0]) if bpm_list else None

        # Extract producers
        producers = get_producers()

        return Song(
            file_id=file_id,
            path=path,
            title=title,
            duration=duration,
            bpm=bpm,
            performers=deduplicate(performers),
            composers=deduplicate(composers),
            lyricists=deduplicate(lyricists),
            producers=deduplicate(producers),
            groups=deduplicate(groups),
        )

    @staticmethod
    def get_raw_tags(path: str) -> dict:
        """
        Extract all raw ID3 tags from the file.
        Returns a dictionary of {Key: Value}.
        """
        try:
            tags = ID3(path)
            raw_data = {}
            for frame_key in tags.keys():
                frame = tags[frame_key]
                # Try to get a human readable description or key
                key = frame_key
                val = str(frame)
                
                # Unwrap text frames if possible to look nicer
                if hasattr(frame, 'text'):
                     val = ", ".join([str(t) for t in frame.text])
                
                raw_data[key] = val
            return raw_data
        except Exception as e:
            print(f"Error reading raw tags: {e}")
            return {}

