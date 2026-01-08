# 🎵 IDEA: Auto Audio Analysis on Import

**Status:** Future (Post-0.1)  
**Complexity:** Medium  
**Value:** High — save manual work on every import

---

## Goal

When importing a song, automatically detect:
1. **BPM** — for mixing and tempo filtering
2. **Cue In** — where music actually starts (skip silence/intro)
3. **Cue Out** — where music ends (before trailing silence)
4. **Has Vocals** — instrumental vs. vocal track

---

## Libraries

| Task | Library | Install | Difficulty |
|------|---------|---------|------------|
| BPM | `librosa` | `pip install librosa` | Easy |
| Cue Points | `pydub` | `pip install pydub` | Easy |
| Voice Detection | `librosa` (spectral) | Already installed | Medium |
| Voice Segments | `inaSpeechSegmenter` | Complex setup | Hard |

---

## Code Snippets

### BPM Detection (`librosa`)

```python
import librosa

def detect_bpm(file_path: str) -> float:
    y, sr = librosa.load(file_path)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(tempo)
```

### Cue In / Cue Out (`pydub`)

```python
from pydub import AudioSegment
from pydub.silence import detect_leading_silence

def detect_cue_points(file_path: str, threshold_db: int = -40) -> tuple[int, int]:
    """Returns (cue_in_ms, cue_out_ms)"""
    audio = AudioSegment.from_file(file_path)
    
    cue_in_ms = detect_leading_silence(audio, silence_threshold=threshold_db)
    cue_out_ms = len(audio) - detect_leading_silence(
        audio.reverse(), 
        silence_threshold=threshold_db
    )
    
    return cue_in_ms, cue_out_ms
```

### Voice Detection (Simple)

```python
import librosa
import numpy as np

def has_vocals(file_path: str, threshold: float = 0.4) -> bool:
    """Rough detection: is vocal frequency band dominant?"""
    y, sr = librosa.load(file_path)
    stft = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    
    # Vocals typically 100Hz - 4kHz
    vocal_mask = (freqs > 100) & (freqs < 4000)
    vocal_energy = stft[vocal_mask, :].mean()
    total_energy = stft.mean()
    
    vocal_ratio = vocal_energy / total_energy
    return vocal_ratio > threshold
```

---

## Integration Points

### On Import
```python
class ImportService:
    def import_song(self, file_path: str) -> Song:
        song = self._create_song_from_file(file_path)
        
        # Auto-detect if fields are empty
        if not song.bpm:
            song.bpm = self.audio_analyzer.detect_bpm(file_path)
        if not song.cue_in:
            song.cue_in, song.cue_out = self.audio_analyzer.detect_cue_points(file_path)
        
        return song
```

### Side Panel
- Show detected values as suggestions
- User can accept or adjust
- "Analyze" button to re-detect

---

## Performance Considerations

| File Length | BPM Detection | Cue Points | 
|-------------|---------------|------------|
| 3 min song | ~2 sec | ~0.5 sec |
| 5 min song | ~4 sec | ~1 sec |

**Recommendation:** Run on background thread during import, don't block UI.

---

## Dependencies

```
librosa>=0.10.0
pydub>=0.25.0
numpy>=1.24.0
```

Note: `pydub` requires `ffmpeg` to be installed (already needed for transcoding).

---

## MVP vs Full

| Feature | MVP | Full |
|---------|-----|------|
| BPM | ✅ | Confidence score, beat grid |
| Cue In/Out | ✅ | Waveform visualization |
| Has Vocals | ✅ | Vocal segment timestamps |
| Key Detection | ❌ | Camelot wheel integration |
| Mood Detection | ❌ | ML-based mood classification |

---

## Related Ideas

- [IDEA_loudness_normalization.md](IDEA_loudness_normalization.md) — EBU R128
- [IDEA_audio_fingerprinting.md](IDEA_audio_fingerprinting.md) — AcoustID matching
