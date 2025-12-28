"""Metadata extraction service"""
from typing import Optional, List
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError
from ...data.models.song import Song
from ...core.yellberus import FIELDS
from ...core import logger
import mutagen.id3
from mutagen.id3 import ID3, ID3NoHeaderError, TXXX, TIPL, TEXT, COMM, APIC, TKEY, TOLY, TCOM, TDRC, TYER
import json
import os


class MetadataService:
    """Service for extracting metadata from audio files"""

    _id3_map = None

    @classmethod
    def _get_id3_map(cls):
        """Load ID3 mapping once and cache it."""
        if cls._id3_map is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(base_dir, '..', '..', 'resources', 'id3_frames.json')
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        cls._id3_map = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading id3_frames.json: {e}")
                    cls._id3_map = {}
            else:
                cls._id3_map = {}
        return cls._id3_map

    @classmethod
    def extract_from_mp3(cls, path: str, source_id: Optional[int] = None) -> Song:
        """
        Extract metadata from an MP3 file and return a Song object.
        Dynamically maps frames using id3_frames.json (Source of Truth).
        Handles ID3v2.3 '/' separator splitting for lists.
        """
        try:
            audio = MP3(path)
        except Exception as e:
            raise ValueError(f"Unable to read MP3 file: {path}") from e

        duration = audio.info.length if audio.info else None
        
        # Use Cached ID3 Mapping
        id3_map = cls._get_id3_map()

        # Helper to safely get list values, handling ID3v2.3 '/' splitting
        def get_values(frame_val, field_type="text") -> List[str]:
            if frame_val is None:
                return []
                
            values = []
            if hasattr(frame_val, "text"):
                raw_items = frame_val.text
            elif hasattr(frame_val, "people"): # TIPL
                 # Flatten (role, name) to name for simple list integration
                 raw_items = [p[1] for p in frame_val.people if len(p) > 1]
            else:
                # If it doesn't have text/people, and it's a mutagen-like object,
                # we don't know how to read it into a text field.
                if hasattr(frame_val, "__dict__") or "mutagen" in str(type(frame_val)):
                    raw_items = []
                else:
                    raw_items = [frame_val]

            if not isinstance(raw_items, (list, tuple)):
                raw_items = [raw_items]

            for item in raw_items:
                if item is None:
                    continue
                s_item = str(item).strip()
                if not s_item: continue
                
                # ID3v2.3 Splitter Fix: Mutagen may return "A/B" as one item for v2.3
                if field_type == "list" and "/" in s_item:
                    split_items = [x.strip() for x in s_item.split("/") if x.strip()]
                    values.extend(split_items)
                else:
                    values.append(s_item)
            return values

        # 1. Generic Extraction Logic
        song_data = {}
        tags = audio.tags or {}
        
        # Map of "Special" fields that we calculate manually later
        # We exclude them from the generic loop to avoid overwriting with raw data
        COMPLEX_FIELDS = {'recording_year', 'is_done', 'producers'} 

        for frame_key in tags.keys():
            # Handle generic frames (TIT2) and TXXX (TXXX:Description)
            lookup_key = frame_key
            
            frame_def = id3_map.get(lookup_key)
            
            if not frame_def:
                continue
                
            # If string definition (legacy simple map), convert to dict
            if isinstance(frame_def, str):
                continue
                
            field_name = frame_def.get('field')
            field_type = frame_def.get('type', 'text')
            
            if not field_name or field_name in COMPLEX_FIELDS:
                continue
                
            val_list = get_values(tags[frame_key], field_type)
            
            if not val_list:
                continue
                
            if field_type == 'list':
                # MERGE POLICY: Extend existing list, deduplicate later
                # This handles cases like TOLY+TEXT both mapping to 'lyricists'
                current_list = song_data.get(field_name, [])
                if not isinstance(current_list, list):
                    current_list = [str(current_list)] if current_list else []
                current_list.extend(val_list)
                song_data[field_name] = current_list 
                
            elif field_type == 'integer':
                try:
                    song_data[field_name] = int(val_list[0])
                except (ValueError, IndexError):
                    pass
            else:
                song_data[field_name] = val_list[0]

        # Deduplicate all list fields
        for key, val in song_data.items():
            if isinstance(val, list):
                song_data[key] = list(dict.fromkeys(val))

        # 2. Complex Logic / Overrides
        
        # --- TITLE (Aliasing) ---
        # JSON maps TIT2 -> 'title', Song uses 'name'.
        if 'title' in song_data:
            song_data['name'] = song_data.pop('title')

        # --- YEAR (Dual Mode: TDRC / TYER) ---
        # Try TDRC first, then TYER
        year_list = get_values(tags.get('TDRC')) or get_values(tags.get('TYER'))
        if year_list:
            try:
                s = str(year_list[0]).strip()
                song_data['recording_year'] = int(s[:4])
            except (ValueError, IndexError):
                pass

        # --- PRODUCERS (Merge TIPL + TXXX:PRODUCER) ---
        producers = []
        # TIPL
        if 'TIPL' in tags:
            p_frame = tags['TIPL']
            if hasattr(p_frame, 'people'):
                for role, name in p_frame.people:
                    if role.lower() == 'producer':
                        producers.append(name.strip())
        # TXXX:PRODUCER
        if 'TXXX:PRODUCER' in tags:
            producers.extend(get_values(tags['TXXX:PRODUCER'], 'list'))
            
        song_data['producers'] = list(dict.fromkeys(producers)) # Dedupe

        # --- IS DONE (Legacy TKEY / New TXXX) ---
        is_done = False
        # 1. Check TXXX:GOSLING_DONE
        if "TXXX:GOSLING_DONE" in tags:
            raw = get_values(tags["TXXX:GOSLING_DONE"])
            if raw and raw[0].lower() in ["1", "true"]:
                is_done = True
        # 2. Fallback TKEY
        elif "TKEY" in tags:
            raw = get_values(tags["TKEY"])
            if raw and raw[0] == "true": # strict "true", not "Am"
                is_done = True
                
        song_data['is_done'] = is_done
        song_data['duration'] = duration

        # --- FALLBACK: COMPOSERS / LYRICISTS (Union Logic for TCOM) ---
        # If composers/lyricists are empty, check if TCOM contains them?
        # Legacy logic: TCOM was treated as union. 
        # Modern: TCOM -> composers, TEXT/TOLY -> lyricists.
        # We rely on generic extraction for TCOM -> composers.
        
        # 3. Construct Song
        return Song(
            source_id=source_id,
            source=path,
            **song_data
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

    # Alias for compatibility with Playlist/UI
    get_id3 = get_raw_tags

    @classmethod
    def write_tags(cls, song: Song) -> bool:
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
            from ...utils.validation import validate_isrc, sanitize_isrc
            from ...core import logger
            
            if validate_isrc(song.isrc):
                song.isrc = sanitize_isrc(song.isrc)  # Store sanitized version
            else:
                logger.dev_warning(f"Invalid ISRC format: {song.isrc}, skipping ID3 write")
                # Keep DB value, just don't write to ID3
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
            # Use Cached ID3 Mapping from JSON (Spec T-38)
            id3_map = cls._get_id3_map()
            
            field_to_frame = {}
            for frame, info in id3_map.items():
                if isinstance(info, dict) and 'field' in info:
                    field_to_frame[info['field']] = frame
            
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

                # Determine Frame ID
                # 1. Try Yellberus definition (Source of Truth)
                frame_id = field.id3_tag
                
                # 2. Fallback to JSON map if Yellberus is None (Legacy compatibility)
                if not frame_id:
                     frame_id = field_to_frame.get(field.name)
                
                # 3. If still no frame, skip
                if not frame_id:
                     continue
                
                # Delete existing tags for this frame
                try:
                    audio.tags.delall(frame_id)
                except KeyError:
                    pass
                
                # If empty (empty string/list), we leave it deleted
                if not val:
                    continue
                
                # Get Helper Class (Reflection)
                FrameClass = getattr(mutagen.id3, frame_id, None)
                
                # Handle TXXX generic
                if not FrameClass and frame_id.startswith("TXXX:"):
                    desc = frame_id.split(":", 1)[1]
                    audio.tags.add(TXXX(encoding=1, desc=desc, text=str(val)))
                    continue
                
                if not FrameClass:
                    logger.warning(f"Unknown Mutagen class for {frame_id}")
                    continue
                
                # Write
                if isinstance(val, list):
                    audio.tags.add(FrameClass(encoding=1, text=val))
                else:
                    audio.tags.add(FrameClass(encoding=1, text=str(val)))

            # --- COMPLEX FIELDS (Dual Mode / Legacy) ---

            # 1. Year (Dual: TDRC + TYER)
            if song.recording_year is not None:
                audio.tags.delall('TDRC')
                audio.tags.delall('TYER')
                s_year = str(song.recording_year)
                audio.tags.add(TDRC(encoding=1, text=s_year))
                audio.tags.add(TYER(encoding=1, text=s_year))

            # 2. Producers (Dual: TIPL + TXXX:PRODUCER)
            if song.producers:
                audio.tags.delall('TIPL')
                audio.tags.delall('TXXX:PRODUCER')
                
                # TIPL
                people_list = [(role, name) for name in song.producers for role in ['producer']]
                audio.tags.add(TIPL(encoding=1, people=people_list))
                
                # TXXX
                audio.tags.add(TXXX(encoding=1, desc='PRODUCER', text=song.producers))
            else:
                 audio.tags.delall('TIPL')
                 audio.tags.delall('TXXX:PRODUCER')

            # 3. Is Done (Dual: TKEY + TXXX:GOSLING_DONE)
            audio.tags.delall('TKEY')
            audio.tags.delall('TXXX:GOSLING_DONE')
            audio.tags.add(TKEY(encoding=1, text=['true' if song.is_done else '']))
            audio.tags.add(TXXX(encoding=1, desc='GOSLING_DONE', text=['1' if song.is_done else '0']))

            # 4. Author Union (Legacy: TCOM = Composers + Lyricists)
            audio.tags.delall('TCOM')
            audio.tags.delall('TEXT')
            audio.tags.delall('TOLY')
            
            # Write Modern Lyricists
            if song.lyricists:
                audio.tags.add(TEXT(encoding=1, text=song.lyricists))
                audio.tags.add(TOLY(encoding=1, text=song.lyricists))

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
                audio.tags.add(TCOM(encoding=1, text=union_list))
            else:
                 pass # TCOM cleared.

            # Save
            # Save
            # User Directive: Output MUST be ID3v2.4
            audio.save(v1=1, v2_version=4)
            return True

        except Exception as e:
            from src.core import logger
            logger.error(f"Error writing tags to {song.path}: {e}")
            return False
