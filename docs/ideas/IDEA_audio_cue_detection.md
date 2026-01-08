# 🎯 IDEA: Audio Cue Detection (News Outro Trigger)

**Status:** Future / Standalone Tool  
**Complexity:** Medium  
**Value:** Very High — automates manual fade timing for news rebroadcast

---

## Problem

We rebroadcast news at scheduled times. The news ends with the same 5-10 second outro jingle every time. Currently, someone has to manually watch and hit "fade out" at the right moment.

**Goal:** Detect the outro jingle in real-time and trigger an action (fade, button press, etc.)

---

## Use Cases

### 1. Integrated with Gosling 2 (Future)
- Stream comes in → detector hears outro → Gosling triggers fade

### 2. Standalone Bot for Legacy App (Immediate!)
- Runs on same PC as old automation software
- Listens to audio output (loopback)
- When outro detected → `pyautogui.press('f')` to trigger fade in old app
- **Zero integration needed** — just listens and clicks

---

## Architecture

### Standalone Bot (Quick Win)

```
┌─────────────────┐
│  Audio Loopback │  (what speakers are playing)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cue Detector   │  (fingerprint matching)
│  "Is this the   │
│   outro?"       │
└────────┬────────┘
         │ YES
         ▼
┌─────────────────┐
│  pyautogui      │  → Send keystroke to old app
│  .press('f')    │
└─────────────────┘
```

### Dependencies

```
pip install pyaudio numpy scipy pyautogui
```

---

## Detection Methods

### Method 1: Cross-Correlation (Simplest)

```python
import numpy as np
from scipy import signal
import librosa

# Load reference outro (once at startup)
reference, sr = librosa.load("news_outro.mp3", sr=22050, mono=True)

def is_outro_playing(audio_chunk: np.ndarray) -> bool:
    """Check if the outro is playing in this chunk"""
    if len(audio_chunk) < len(reference):
        return False
    
    correlation = signal.correlate(audio_chunk, reference, mode='valid')
    max_corr = np.max(np.abs(correlation))
    normalized = max_corr / (np.linalg.norm(audio_chunk) * np.linalg.norm(reference))
    
    return normalized > 0.7  # Tune this threshold
```

### Method 2: Spectrogram Template Matching

```python
import librosa
from skimage.feature import match_template

# Reference spectrogram (once)
ref_y, sr = librosa.load("news_outro.mp3")
ref_spec = librosa.feature.melspectrogram(y=ref_y, sr=sr)

def find_outro(stream_buffer: np.ndarray) -> tuple[bool, float]:
    """Returns (found, time_offset_seconds)"""
    stream_spec = librosa.feature.melspectrogram(y=stream_buffer, sr=sr)
    result = match_template(stream_spec.T, ref_spec.T)  # Transpose for time axis
    
    match_score = np.max(result)
    if match_score > 0.75:
        match_frame = np.argmax(result)
        match_time = librosa.frames_to_time(match_frame, sr=sr)
        return True, match_time
    return False, 0
```

---

## Standalone Bot Script

```python
"""
News Outro Detector Bot
Listens for outro jingle, triggers keystroke in old automation app.
"""

import pyaudio
import numpy as np
from scipy import signal
import librosa
import pyautogui
import time

# Config
OUTRO_FILE = "news_outro.mp3"
SAMPLE_RATE = 22050
BUFFER_SECONDS = 12  # Keep 12 seconds of audio
CHECK_INTERVAL = 0.5  # Check twice per second
THRESHOLD = 0.7
TRIGGER_KEY = 'f'  # Key to press in old app
COOLDOWN_SECONDS = 60  # Don't trigger again for 60 sec

# Load reference
print(f"Loading reference: {OUTRO_FILE}")
reference, _ = librosa.load(OUTRO_FILE, sr=SAMPLE_RATE, mono=True)
print(f"Reference loaded: {len(reference)/SAMPLE_RATE:.1f} seconds")

# Rolling buffer
buffer = np.zeros(BUFFER_SECONDS * SAMPLE_RATE, dtype=np.float32)
last_trigger = 0

def audio_callback(in_data, frame_count, time_info, status):
    global buffer, last_trigger
    
    # Add new samples to buffer (rolling)
    samples = np.frombuffer(in_data, dtype=np.float32)
    buffer = np.roll(buffer, -len(samples))
    buffer[-len(samples):] = samples
    
    return (None, pyaudio.paContinue)

def check_for_outro():
    global last_trigger
    
    if time.time() - last_trigger < COOLDOWN_SECONDS:
        return  # Still in cooldown
    
    # Run correlation
    correlation = signal.correlate(buffer, reference, mode='valid')
    max_corr = np.max(np.abs(correlation))
    norm = np.linalg.norm(buffer) * np.linalg.norm(reference)
    
    if norm > 0:
        score = max_corr / norm
        if score > THRESHOLD:
            print(f"🎯 OUTRO DETECTED! Score: {score:.2f}")
            print(f"   Pressing '{TRIGGER_KEY}' in 3 seconds...")
            time.sleep(3)  # Wait for outro to finish
            pyautogui.press(TRIGGER_KEY)
            print(f"   ✓ Key pressed!")
            last_trigger = time.time()

def main():
    # Setup audio input (loopback)
    p = pyaudio.PyAudio()
    
    # Find loopback device (WASAPI on Windows)
    device_index = None
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if "loopback" in info['name'].lower() or "stereo mix" in info['name'].lower():
            device_index = i
            print(f"Using device: {info['name']}")
            break
    
    if device_index is None:
        print("ERROR: No loopback device found. Enable 'Stereo Mix' in Windows sound settings.")
        return
    
    stream = p.open(
        format=pyaudio.paFloat32,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=1024,
        stream_callback=audio_callback
    )
    
    print("🎧 Listening for outro...")
    stream.start_stream()
    
    try:
        while True:
            check_for_outro()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopping...")
    
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    main()
```

---

## Testing

1. Record the news outro as `news_outro.mp3` (just the jingle, 5-10 sec)
2. Run the bot
3. Play the news stream
4. Watch it detect and trigger!

**Tuning:**
- Adjust `THRESHOLD` if false positives/negatives
- Adjust `COOLDOWN_SECONDS` for your news schedule
- Adjust `time.sleep(3)` for precise fade timing

---

## Windows Audio Loopback

To capture "what's playing on speakers":

1. **Option A:** Enable "Stereo Mix" 
   - Right-click speaker icon → Sounds → Recording → Enable "Stereo Mix"

2. **Option B:** Use WASAPI loopback
   - Requires `sounddevice` with WASAPI backend
   - More reliable, lower latency

```python
import sounddevice as sd
# List devices with loopback
print(sd.query_devices())
```

---

## Future Enhancements

- [ ] GUI with waveform display
- [ ] Multiple cue detection (different outros for different shows)
- [ ] Network trigger (send HTTP request instead of keypress)
- [ ] Confidence logging for tuning
- [ ] Integration with Gosling 2 playback engine

---

## Related

- [IDEA_auto_audio_analysis.md](IDEA_auto_audio_analysis.md) — BPM, cue detection
- [IDEA_silence_detection.md](IDEA_silence_detection.md) — Silence/dead air detection
