# Feature Request: Future Radio Automation Capabilities (Wishlist)

*This file serves as a local backlog for features **NOT yet tracked** in the main GitHub issues. It is intended to eventually be posted as a new issue (e.g., "Future Wishlist").*

This is a tracking list for long-term features required for a professional radio environment, to be implemented **after** Phases 1-4 of `plan.md` are complete.

## 🎛️ Audio Processing & Output
- [ ] **DSP / VST Support**: Integration for VST plugins (compressor, limiter, EQ) on the master output to ensure loud, consistent broadcast sound.
- [ ] **Built-in Streaming Encoder**: Direct streaming to Icecast/Shoutcast servers (MP3/AAC) without needing external tools like BUTT or Breakaway.
- [ ] **Multiple Outputs**: Separate audio device configuration for "Cue" (Headphones) and "Air" (Speakers/Stream).

## 🔌 Hardware & External Integration
- [ ] **GPIO / Fader Start**: Support for triggering playback via serial port or USB game controllers (simulating mixing console fader starts).
- [ ] **MIDI Control**: Support for MIDI surfaces to control faders/buttons physically.
- [ ] **Metadata Push**: HTTP GET/POST callbacks to push "Now Playing" data to websites, RDS encoders, or mobile apps.

## 🛠️ Advanced Tools
- [ ] **Silence Detector**: Automatic email alert or failover mode if silence is detected for >10 seconds.
- [ ] **Voice Tracking Recorder**: A dedicated interface to record voice links while listening to the "tail" of the previous song and "intro" of the next.
- [ ] **Traffic/Billing Generator**: Specialized scheduler for commercials to ensure separation (e.g., don't play two car ads back-to-back) and proof-of-play generation.
