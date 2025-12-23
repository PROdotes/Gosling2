# IDEA: MediaItem Composition Pattern

> **Status**: 💡 Idea  
> **Context**: Radio automation requires handling Songs, Jingles, VoiceTracks, Ads  
> **Author**: Vesper  
> **Date**: 2025-12-23

---

## Problem

The `Song` model works for music, but radio automation needs other media types:
- Jingles (station IDs, bumpers)
- Voice Tracks (presenter links)
- Adverts (commercials with expiry dates)

The current `Song` object has music-specific fields (album, artist, composer) that don't apply to jingles.

---

## Proposed Solution: Option 3 (Composition)

Mirror the existing database structure in code:

### Database (already exists)
```
MediaSources (TypeID, Path, Duration, ...)
     ├── Songs (BPM, Year, ISRC, ...)
     ├── [future: Jingles table]
     └── [future: VoiceTracks table]
```

### Code (proposed)
```python
@dataclass
class MediaItem:
    # Base fields (from MediaSources)
    source_id: int
    path: str
    name: str
    duration: float
    type: MediaType  # SONG, JINGLE, VOICETRACK, AD
    
    # Type-specific extensions (composition, not inheritance)
    song: Optional[Song] = None
    jingle: Optional[Jingle] = None
    voice_track: Optional[VoiceTrack] = None
```

### Usage
```python
# Playlist can hold any MediaItem
playlist: List[MediaItem] = []

for item in playlist:
    if item.type == MediaType.SONG:
        print(f"Now playing: {item.song.title} by {item.song.unified_artist}")
    elif item.type == MediaType.JINGLE:
        print(f"Jingle: {item.jingle.category}")
```

---

## Why Composition over Inheritance

1. **Matches DB structure** — MediaSources is already the base table
2. **Song model unchanged** — Existing code keeps working
3. **Flexible** — Easy to add new types without modifying base class
4. **Single query path** — All types use same yellberus/query system

---

## Related

- T-22: Albums (might need similar thinking for Album as a playable unit)
- Type Tabs (already filter by TypeID)

---

*Logged by Vesper per [ZERO_LOSS] protocol*
