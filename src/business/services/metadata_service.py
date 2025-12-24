"""Metadata extraction service"""
from typing import Optional, List
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError
from ...data.models.song import Song
from ...core.yellberus import FIELDS
import mutagen.id3
from mutagen.id3 import ID3, ID3NoHeaderError, TXXX, TIPL, TEXT, COMM, APIC
import json
import os


class MetadataService:
    """Service for extracting metadata from audio files"""

    @staticmethod
    def extract_from_mp3(path: str, source_id: Optional[int] = None) -> Song:
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

        # Extract Album
        album_list = get_text_list("TALB")
        album = album_list[0] if album_list else None

        # Extract Album Artist
        album_artist_list = get_text_list("TPE2")
        album_artist = album_artist_list[0] if album_artist_list else None

        return Song(
            source_id=source_id,
            source=path,
            name=title,
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
            album=album,
            album_artist=album_artist,
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
        Dynamically uses yellberus.FIELDS and id3_frames.json for mapping.
        Handles Dual-Mode fields (Year, Done, Producers) and Legacy Union (TCOM) specifically.
        Returns True on success, False on failure.
        """
        if not song.path:
            return False

        # --- VALIDATION ---
        from datetime import datetime
        current_year = datetime.now().year
        
        # Validate Year
        if song.recording_year is not None:
            if song.recording_year < 1860 or song.recording_year > current_year + 1:
                print(f"Warning: Invalid year {song.recording_year}, skipping year write")
                song.recording_year = None

        # Validate ISRC
        if song.isrc:
            import re
            isrc_pattern = r'^[A-Z]{2}-?[A-Z0-9]{3}-?\d{2}-?\d{5}$'
            if not re.match(isrc_pattern, song.isrc.replace('-', '')):
                print(f"Warning: Invalid ISRC format {song.isrc}, skipping ISRC write")
                song.isrc = None

        # Validate BPM
        if song.bpm is not None and song.bpm <= 0:
            print(f"Warning: Invalid BPM {song.bpm}, skipping BPM write")
            song.bpm = None

        # Validate Lengths
        MAX_TEXT_LENGTH = 1000
        if song.title and len(song.title) > MAX_TEXT_LENGTH:
            song.title = song.title[:MAX_TEXT_LENGTH]
        if song.isrc and len(song.isrc) > 50:
            song.isrc = song.isrc[:50]

        # Clean Lists Helper
        def clean_list(items):
            if not items: return []
            return [str(item).strip() for item in items if item and str(item).strip()]

        # Clean all list fields
        if song.performers: song.performers = clean_list(song.performers)
        if song.composers: song.composers = clean_list(song.composers)
        if song.lyricists: song.lyricists = clean_list(song.lyricists)
        if song.producers: song.producers = clean_list(song.producers)
        if song.groups: song.groups = clean_list(song.groups)

        try:
            # Load ID3 Mapping from JSON (Spec T-38)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(base_dir, '..', '..', 'resources', 'id3_frames.json')
            
            field_to_frame = {}
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for frame, info in data.items():
                        if isinstance(info, dict) and 'field' in info:
                            field_to_frame[info['field']] = frame
            else:
                print(f"Warning: id3_frames.json not found at {json_path}")
            
            # Alias mapping (JSON uses "title", Song uses "name" but field def uses "title")
            # yellberus.FIELDS uses "title" as name, so we are good.
            # But just in case, Yellberus field.name should match JSON field.

            # Open File
            audio = MP3(song.path, ID3=ID3)
            if audio.tags is None: audio.add_tags()

            # --- DYNAMIC WRITE LOOP ---
            # Fields to exclude from loop because they have special complex handling
            COMPLEX_FIELDS = {
                'recording_year', 'is_done', 'producers', 'composers', 'lyricists', 'unified_artist'
            }

            for field in FIELDS:
                if not field.portable:
                    continue
                
                if field.name in COMPLEX_FIELDS:
                    continue
                
                # Get Value
                val = getattr(song, field.name, None)
                
                # SPARSE UPDATE: If None, preserve existing tag (do not delete)
                if val is None:
                    continue

                # Determine Frame ID from JSON Map
                frame_id = field_to_frame.get(field.name)
                
                # Fallback check (e.g. isrc -> TSRC)
                if not frame_id:
                     # Some fields might not be in JSON yet?
                     continue
                
                # Delete existing tags for this frame
                audio.tags.delall(frame_id)
                
                # If empty (empty string/list), we leave it deleted
                if not val:
                    continue
                
                # Get Helper Class (Reflection)
                FrameClass = getattr(mutagen.id3, frame_id, None)
                
                # Handle TXXX generic
                if not FrameClass and frame_id.startswith("TXXX:"):
                    desc = frame_id.split(":", 1)[1]
                    audio.tags.add(TXXX(encoding=3, desc=desc, text=str(val)))
                    continue
                
                if not FrameClass:
                    print(f"Warning: Unknown Mutagen class for {frame_id}")
                    continue
                
                # Write
                if isinstance(val, list):
                    audio.tags.add(FrameClass(encoding=3, text=val))
                else:
                    audio.tags.add(FrameClass(encoding=3, text=str(val)))

            # --- COMPLEX FIELDS (Dual Mode / Legacy) ---

            # 1. Year (Dual: TDRC + TYER)
            if song.recording_year is not None:
                audio.tags.delall('TDRC')
                audio.tags.delall('TYER')
                from mutagen.id3 import TDRC, TYER
                s_year = str(song.recording_year)
                audio.tags.add(TDRC(encoding=3, text=s_year))
                audio.tags.add(TYER(encoding=3, text=s_year))

            # 2. Producers (Dual: TIPL + TXXX:PRODUCER)
            if song.producers:
                audio.tags.delall('TIPL')
                audio.tags.delall('TXXX:PRODUCER')
                
                # TIPL
                people_list = [(role, name) for name in song.producers for role in ['producer']]
                audio.tags.add(TIPL(encoding=3, people=people_list))
                
                # TXXX
                audio.tags.add(TXXX(encoding=3, desc='PRODUCER', text=song.producers))
            else:
                 audio.tags.delall('TIPL')
                 audio.tags.delall('TXXX:PRODUCER')

            # 3. Is Done (Dual: TKEY + TXXX:GOSLING_DONE)
            audio.tags.delall('TKEY')
            audio.tags.delall('TXXX:GOSLING_DONE')
            from mutagen.id3 import TKEY
            audio.tags.add(TKEY(encoding=3, text='true' if song.is_done else ' '))
            audio.tags.add(TXXX(encoding=3, desc='GOSLING_DONE', text='1' if song.is_done else '0'))

            # 4. Author Union (Legacy: TCOM = Composers + Lyricists)
            audio.tags.delall('TCOM')
            audio.tags.delall('TEXT')
            audio.tags.delall('TOLY')
            
            # Write Modern Lyricists
            if song.lyricists:
                from mutagen.id3 import TCOM, TEXT, TOLY
                audio.tags.add(TEXT(encoding=3, text=song.lyricists))
                audio.tags.add(TOLY(encoding=3, text=song.lyricists))

            # Write TCOM Union (Jazler Hack)
            union_list = []
            seen = set()
            for c in (song.composers or []):
                if c not in seen:
                    union_list.append(c)
                    seen.add(c)
            for l in (song.lyricists or []):
                if l not in seen:
                    union_list.append(l)
                    seen.add(l)
            
            if union_list:
                from mutagen.id3 import TCOM
                audio.tags.add(TCOM(encoding=3, text=union_list))

            # Save
            audio.save(v1=1)
            return True

        except Exception as e:
            print(f"Error writing tags to {song.path}: {e}")
            return False

