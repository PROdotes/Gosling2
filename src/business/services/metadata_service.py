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

        # Helper to extract Done flag (Dual Mode)
        def get_is_done() -> bool:
            # 1. Check TXXX:GOSLING_DONE (New Standard)
            if "TXXX:GOSLING_DONE" in tags:
                raw_list = get_text_list("TXXX:GOSLING_DONE")
                if raw_list:
                    val = raw_list[0].strip().lower()
                    return val in ["1", "true"]
            
            # 2. Fallback to TKEY (Legacy)
            if "TKEY" in tags:
                raw_list = get_text_list("TKEY")
                if raw_list:
                    val = raw_list[0] # Do not strip! " " is meant to be false.
                    if val == "true":
                        return True
                    # If val is a real key (e.g. "Am", "12B"), we do NOT consider it Done.
                    # Legacy logic only wrote "true" or " ".
            
            return False

        # Extract title (use get_text_list for consistency)
        title_list = get_text_list("TIT2")
        title = title_list[0] if title_list else None

        # Extract contributors
        performers = get_text_list("TPE1")
        composers = get_text_list("TCOM")
        lyricists = get_text_list("TOLY") or get_text_list("TEXT")
        groups = get_text_list("TIT1")
        
        # Extract ISRC
        isrc_list = get_text_list("TSRC")
        isrc = isrc_list[0] if isrc_list else None

        # Extract IsDone
        is_done = get_is_done()

        # Extract BPM
        bpm_list = get_text_list("TBPM")
        bpm = int(bpm_list[0]) if bpm_list else None

        # Extract Year
        year_list = get_text_list("TDRC") or get_text_list("TYER")
        recording_year = None
        if year_list:
            try:
                # TDRC might be "2023-01-01", TYER "2023"
                s = str(year_list[0]).strip()
                # Take first 4 digits
                recording_year = int(s[:4])
            except (ValueError, IndexError):
                pass

        # Extract producers
        producers = get_producers()

        return Song(
            file_id=file_id,
            path=path,
            title=title,
            isrc=isrc,
            duration=duration,
            bpm=bpm,
            recording_year=recording_year,
            is_done=is_done,
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

    @staticmethod
    def write_tags(song: Song) -> bool:
        """
        Write metadata from Song object to MP3 file.
        Preserves existing frames not managed by Gosling (e.g., APIC album art, COMM comments).
        Returns True on success, False on failure.
        """
        if not song.path:
            return False
        
        # Validate data before writing
        from datetime import datetime
        current_year = datetime.now().year
        
        # Validate year (1860 to current_year + 1)
        if song.recording_year is not None:
            if song.recording_year < 1860 or song.recording_year > current_year + 1:
                print(f"Warning: Invalid year {song.recording_year}, skipping year write")
                song.recording_year = None  # Don't write invalid year
        
        # Validate ISRC format (CC-XXX-YY-NNNNN)
        if song.isrc:
            import re
            isrc_pattern = r'^[A-Z]{2}-?[A-Z0-9]{3}-?\d{2}-?\d{5}$'
            if not re.match(isrc_pattern, song.isrc.replace('-', '')):
                print(f"Warning: Invalid ISRC format {song.isrc}, skipping ISRC write")
                song.isrc = None  # Don't write invalid ISRC
        
        # Validate BPM (positive integer)
        if song.bpm is not None and song.bpm <= 0:
            print(f"Warning: Invalid BPM {song.bpm}, skipping BPM write")
            song.bpm = None
        
        # Validate string lengths (prevent ID3 corruption from oversized data)
        MAX_TEXT_LENGTH = 1000
        if song.title and len(song.title) > MAX_TEXT_LENGTH:
            print(f"Warning: Title too long ({len(song.title)} chars), truncating to {MAX_TEXT_LENGTH}")
            song.title = song.title[:MAX_TEXT_LENGTH]
        
        if song.isrc and len(song.isrc) > 50:  # ISRC should be 12 chars max
            print(f"Warning: ISRC too long, truncating")
            song.isrc = song.isrc[:50]
        
        # Validate and clean lists (remove empty/invalid items)
        def clean_list(items):
            """Remove empty strings, None, and non-strings from list"""
            if not items:
                return []
            return [str(item).strip() for item in items if item and str(item).strip()]
        
        if song.performers:
            song.performers = clean_list(song.performers)
        if song.composers:
            song.composers = clean_list(song.composers)
        if song.lyricists:
            song.lyricists = clean_list(song.lyricists)
        if song.producers:
            song.producers = clean_list(song.producers)
        if song.groups:
            song.groups = clean_list(song.groups)
        
        try:
            from mutagen.id3 import TIT2, TPE1, TCOM, TEXT, TOLY, TBPM, TDRC, TSRC, TKEY, TXXX, TIT1, TIPL
            
            # Load file
            audio = MP3(song.path, ID3=ID3)
            
            # Ensure tags exist
            if audio.tags is None:
                audio.add_tags()
            
            # Update title (only if not None/empty)
            if song.title:
                audio.tags.delall('TIT2')
                audio.tags.add(TIT2(encoding=3, text=song.title))
            
            # Update performers (handle list)
            if song.performers:
                audio.tags.delall('TPE1')
                audio.tags.add(TPE1(encoding=3, text=song.performers))
            
            # Update composers
            if song.composers:
                audio.tags.delall('TCOM')
                audio.tags.add(TCOM(encoding=3, text=song.composers))
            
            # Update lyricists (use TEXT, which is the standard frame)
            if song.lyricists:
                audio.tags.delall('TEXT')
                audio.tags.delall('TOLY')  # Also clear legacy frame
                audio.tags.add(TEXT(encoding=3, text=song.lyricists))
            
            # Update groups
            if song.groups:
                audio.tags.delall('TIT1')
                audio.tags.add(TIT1(encoding=3, text=song.groups))
            
            # Update BPM
            if song.bpm is not None:
                audio.tags.delall('TBPM')
                audio.tags.add(TBPM(encoding=3, text=str(song.bpm)))
            
            # Update recording year
            if song.recording_year is not None:
                audio.tags.delall('TDRC')
                audio.tags.delall('TYER')  # Also clear legacy frame
                audio.tags.add(TDRC(encoding=3, text=str(song.recording_year)))
            
            # Update ISRC
            if song.isrc:
                audio.tags.delall('TSRC')
                audio.tags.add(TSRC(encoding=3, text=song.isrc))
            
            # Update producers (dual mode: TIPL + TXXX:PRODUCER)
            if song.producers:
                # TIPL format: list of (role, name) tuples
                audio.tags.delall('TIPL')
                people_list = [(role, name) for name in song.producers for role in ['producer']]
                audio.tags.add(TIPL(encoding=3, people=people_list))
                
                # Also write to TXXX:PRODUCER for compatibility
                audio.tags.delall('TXXX:PRODUCER')
                audio.tags.add(TXXX(encoding=3, desc='PRODUCER', text=song.producers))
            
            # Update is_done (dual mode: TKEY + TXXX:GOSLING_DONE)
            audio.tags.delall('TKEY')
            audio.tags.delall('TXXX:GOSLING_DONE')
            audio.tags.add(TKEY(encoding=3, text='true' if song.is_done else ' '))
            audio.tags.add(TXXX(encoding=3, desc='GOSLING_DONE', text='1' if song.is_done else '0'))
            
            # Save file (v1=1 preserves existing ID3v1, doesn't create new)
            audio.save(v1=1)
            return True
            
        except Exception as e:
            print(f"Error writing tags to {song.path}: {e}")
            return False

