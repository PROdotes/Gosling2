from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError


class Song:
    def __init__(
            self,
            file_id=None,
            path=None,
            title=None,
            duration=None,
            bpm=None,
            performers=None,
            composers=None,
            lyricists=None,
            producers=None,
            groups=None,
    ):
        self.file_id = file_id
        self.path = path
        self.title = title
        self.duration = duration
        self.bpm = bpm

        self.performers = performers or []
        self.composers = composers or []
        self.lyricists = lyricists or []
        self.producers = producers or []
        self.groups = groups or []

    @classmethod
    def from_mp3(cls, path: str, file_id_input):
        """
        Load an MP3 file and extract normalized metadata into a Song object.
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
                # mutagen stores text frames in f.text (list)
                if hasattr(f, "text"):
                    for item in f.text:
                        if item:
                            values.append(str(item).strip())
            return values

        title = None
        if "TIT2" in tags:
            title_items = tags.getall("TIT2")[0].text
            title = title_items[0].strip() if title_items else None

        # Domain mappings
        performers = get_text_list("TPE1")
        composers = get_text_list("TCOM")
        lyricists = get_text_list("TOLY") or get_text_list("TEXT")
        groups = get_text_list("TIT1")

        # Tempo/BPM
        bpm_list = get_text_list("TBPM")
        bpm = int(bpm_list[0]) if bpm_list else None

        # Producers: no standard tag. Use TIPL or your own TXXX(PRODUCER)
        producers = []
        if "TIPL" in tags:  # Involved People List
            for p in tags.getall("TIPL"):
                if hasattr(p, "people"):
                    for role, name in p.people:
                        if role.lower() == "producer":
                            producers.append(name.strip())

        # Optional: custom TXXX frame (your choice)
        if "TXXX:PRODUCER" in tags:
            producers.extend(get_text_list("TXXX:PRODUCER"))

        return cls(
            file_id=file_id_input,
            path=path,
            title=title,
            duration=duration,
            bpm=bpm,
            performers=list(dict.fromkeys(performers)),  # dedupe while preserving order
            composers=list(dict.fromkeys(composers)),
            lyricists=list(dict.fromkeys(lyricists)),
            producers=list(dict.fromkeys(producers)),
            groups=list(dict.fromkeys(groups)),
        )
