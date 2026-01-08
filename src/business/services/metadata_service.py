"""Metadata extraction service"""
import os
from typing import Optional, List
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError
from ...data.models.song import Song
from ...core.yellberus import FIELDS
from ...core import logger
from ...core.registries.id3_registry import ID3Registry
import mutagen.id3
from mutagen.id3 import ID3, ID3NoHeaderError, TXXX, TIPL, TEXT, COMM, APIC, TKEY, TOLY, TCOM, TDRC, TYER, TLEN


class MetadataService:
    """Service for extracting metadata from audio files"""

    @classmethod
    def _get_id3_map(cls):
        """
        DEPRECATED: Use ID3Registry.get_frame_map() directly.
        Kept for backward compatibility with Song.from_row().
        """
        return ID3Registry.get_frame_map()

    @classmethod
    def extract_metadata(cls, path: str, source_id: Optional[int] = None) -> Song:
        """
        Generic entry point for metadata extraction.
        Supports MP3 (ID3) and WAV (RIFF).
        Enforces a name (title) fallback to filename if retrieval fails.
        """
        ext = path.lower().split('.')[-1]
        if ext == 'wav':
            song = cls.extract_from_wav(path, source_id)
        else:
            song = cls.extract_from_mp3(path, source_id)
            
        # SAFETY: Ensure Name is never None (prevent DB NOT NULL crashes)
        if not song.name or not song.name.strip():
            base = os.path.basename(path)
            # Remove extension for cleaner title
            song.name = os.path.splitext(base)[0]
            
        return song

    @classmethod
    def extract_from_wav(cls, path: str, source_id: Optional[int] = None) -> Song:
        """Extract metadata from WAV (RIFF) using basic mapping."""
        from mutagen.wave import WAVE
        try:
            audio = WAVE(path)
        except Exception as e:
            return Song(source_id=source_id, source=path)

        # WAV/RIFF has very limited standard tags (INFO chunk)
        tags = audio.tags if audio.tags else {}
        song = Song(source_id=source_id, source=path)
        song.duration = audio.info.length if audio.info else None
        
        # Simple RIFF Map (Standard "INFO" keys)
        # INAM: Title, IART: Artist, IPRD: Album, ICRD: Year, IGNR: Genre
        # Title (INAM=RIFF, TIT2=ID3)
        title_val = tags.get('INAM') or tags.get('TIT2')
        if title_val: song.name = str(title_val).strip()
        
        # Artist (IART=RIFF, TPE1=ID3)
        artist_val = tags.get('IART') or tags.get('ARTIST') or tags.get('TPE1')
        if artist_val:
             song.performers = [str(artist_val).strip()]
             
        # Album (IPRD=RIFF, TALB=ID3)
        album_val = tags.get('IPRD') or tags.get('TALB')
        if album_val: song.album = str(album_val).strip()

        if 'ICRD' in tags: 
            try: song.recording_year = int(str(tags['ICRD'])[:4])
            except: pass
        
        return song

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
        
        # FALLBACK: If duration is 0 (VBR glitch), try TLEN (Length in ms)
        if (not duration or duration == 0) and audio.tags and 'TLEN' in audio.tags:
             try:
                 # TLEN is string in ms
                 raw_tlen = str(audio.tags['TLEN'].text[0])
                 ms = int(raw_tlen)
                 if ms > 0: 
                     duration = ms / 1000.0
             except Exception: 
                 pass
        
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
        COMPLEX_FIELDS = {'recording_year', 'is_done', 'producers', 'genre', 'mood'} 

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

        # STATUS: No longer extracted here. The TagRepository is the source of truth.
        # The Yellberus query calculates is_done as a virtual column from tag presence.
        
        song_data['duration'] = duration

        # --- TAGS (Extract Mapped Categories) ---
        tags_list = []
        
        # Pull Category Mappings from JSON
        for frame_key, frame_def in id3_map.items():
            if not isinstance(frame_def, dict): continue
            
            cat = frame_def.get('tag_category')
            if cat and tags and frame_key in tags:
                values = get_values(tags[frame_key], 'list')
                for v in values:
                    tags_list.append(f"{cat}:{v}")
                    
        song_data['tags'] = list(dict.fromkeys(tags_list))
        
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

        # --- VALIDATION (Fail-Safe) ---
        # Centralized Yellberus Validation: Improves data before writing to ID3.
        from ...core import yellberus
        for field in yellberus.FIELDS:
             if not field.portable: continue
             attr = field.model_attr or field.name
             val = getattr(song, attr, None)
             if val is None: continue
             
             # 1. Clean Lists (Remove None/'')
             if field.field_type == yellberus.FieldType.LIST and isinstance(val, list):
                 val = [str(v).strip() for v in val if v and str(v).strip()]
                 setattr(song, attr, val)
                 
             # 2. Truncate Fields (Fail-Safe Overflow)
             if field.max_length and isinstance(val, str) and len(val) > field.max_length:
                 val = val[:field.max_length]
                 setattr(song, attr, val)

             # 3. Final Policy Check
             if not field.is_valid(val):
                 from src.core import logger
                 logger.dev_warning(f"MetadataService: Dropping invalid value '{val}' for field '{field.name}'")
                 setattr(song, attr, None)




        try:
            # Use Cached ID3 Mapping from JSON (Spec T-38)
            id3_map = cls._get_id3_map()
            LIST_SEP = " / " # Radio-safe separator (No nulls)
            
            field_to_frame = {}
            for frame, info in id3_map.items():
                if isinstance(info, dict) and 'field' in info:
                    field_to_frame[info['field']] = frame
            
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
                frame_id = field.id3_tag
                if not frame_id:
                     frame_id = field_to_frame.get(field.name)
                
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
                    # Join lists for TXXX too
                    txt_val = LIST_SEP.join(val) if isinstance(val, list) else str(val)
                    audio.tags.add(TXXX(encoding=1, desc=desc, text=[txt_val]))
                    continue
                
                if not FrameClass:
                    logger.warning(f"Unknown Mutagen class for {frame_id}")
                    continue
                
                # Write: Use native lists for ID3v2.4 (Mutagen handles null separation)
                if isinstance(val, list):
                    audio.tags.add(FrameClass(encoding=1, text=val))
                else:
                    audio.tags.add(FrameClass(encoding=1, text=[str(val)]))

            # --- DYNAMIC TAG CATEGORY WRITE ---
            # Look for frames mapped to tag categories in the JSON map
            for frame_id, frame_def in id3_map.items():
                if not isinstance(frame_def, dict): continue
                
                cat = frame_def.get('tag_category')
                if not cat: continue
                
                # Resolve from unified tags
                prefix = f"{cat}:"
                val = [t.split(':', 1)[1] for t in (song.tags or []) if t.startswith(prefix)]
                
                if not val:
                    continue
                    
                # Direct write to frame
                FrameClass = getattr(mutagen.id3, frame_id, None)
                if not FrameClass and frame_id.startswith("TXXX:"):
                    desc = frame_id.split(":", 1)[1]
                    audio.tags.delall(frame_id)
                    audio.tags.add(TXXX(encoding=1, desc=desc, text=val))
                elif FrameClass:
                    audio.tags.delall(frame_id)
                    audio.tags.add(FrameClass(encoding=1, text=val))

            # --- COMPLEX FIELDS (Dual Mode / Legacy) ---

            # 1. Year (Dual: TDRC + TYER)
            if song.recording_year is not None:
                audio.tags.delall('TDRC')
                audio.tags.delall('TYER')
                s_year = str(song.recording_year)
                audio.tags.add(TDRC(encoding=1, text=[s_year]))
                audio.tags.add(TYER(encoding=1, text=[s_year]))

            # 2. Producers (Dual: TIPL + TXXX:PRODUCER)
            if song.producers:
                audio.tags.delall('TIPL')
                audio.tags.delall('TXXX:PRODUCER')
                
                # TIPL (Mutagen handles this specifically via 'people' list)
                people_list = [(role, name) for name in song.producers for role in ['producer']]
                audio.tags.add(TIPL(encoding=1, people=people_list))
                
                # TXXX Fallback (Joined string for Radio software)
                audio.tags.add(TXXX(encoding=1, desc='PRODUCER', text=[LIST_SEP.join(song.producers)]))
            else:
                 audio.tags.delall('TIPL')
                 audio.tags.delall('TXXX:PRODUCER')

            # 3. Status Tag (Truth) + Legacy Compatibility
            # NOTE: Status is now managed by TagRepository. The caller must pass
            # is_unprocessed if they want to bake the status into ID3.
            # If song has 'is_unprocessed' attr (set by caller), use it.
            audio.tags.delall('TXXX:STATUS')
            audio.tags.delall('TKEY')
            audio.tags.delall('TXXX:GOSLING_DONE') # Cleanup legacy

            is_unprocessed = getattr(song, 'is_unprocessed', None)
            if is_unprocessed is True:
                # Permission NOT granted. Mark as Unprocessed.
                audio.tags.add(TXXX(encoding=1, desc='STATUS', text=['Unprocessed']))
            elif is_unprocessed is False:
                # Permission GRANTED (Done). Write Legacy code for compatibility.
                audio.tags.add(TKEY(encoding=1, text=['true']))
            # If is_unprocessed is None, we don't touch the status tags (sparse update)

            # 4. Author Union (Legacy: TCOM = Composers + Lyricists)
            audio.tags.delall('TCOM')
            audio.tags.delall('TEXT')
            audio.tags.delall('TOLY')
            
            # Write Modern Lyricists (Joined for Radio)
            if song.lyricists:
                lyr_str = LIST_SEP.join(song.lyricists)
                audio.tags.add(TEXT(encoding=1, text=[lyr_str]))
                audio.tags.add(TOLY(encoding=1, text=[lyr_str]))

            # Write TCOM Union (Jazler Hack - Joined for Radio)
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
                audio.tags.add(TCOM(encoding=1, text=[LIST_SEP.join(union_list)]))

            # 5. Duration (TLEN) - Backup for VBR glitches
            if song.duration and song.duration > 0:
                audio.tags.delall('TLEN')
                tlen_ms = str(int(song.duration * 1000))
                audio.tags.add(TLEN(encoding=1, text=[tlen_ms]))

            # Save
            # Save
            # User Directive: Output MUST be ID3v2.4
            audio.save(v1=1, v2_version=4)
            return True

        except Exception as e:
            from src.core import logger
            logger.error(f"Error writing tags to {song.path}: {e}")
            return False
