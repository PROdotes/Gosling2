# Gosling2 - Player & Audio Engine Roadmap (Deferred)

## ⏸️ Status: DEFERRED
**Focus**: Conceptual Design & Wishlist.
**Trigger**: To be started only after the Database and Scheduler (Phase 1-3 of `plan_database.md`) are stable.

---

## 🎧 Phase 4: Audio Engine Overhaul (Issue #7)

The current "Ping-Pong" player is good, but radio needs "Segue" logic, not just crossfading at end of track.
**Source: [Issue #7 - Broadcast Automation & Timing Logic](https://github.com/PROdotes/Gosling2/issues/7)**

### 4.1 Precision Playback
*   **Segue Logic**: The `PlaybackService` must trigger the next event based on the current song's `NextCue`/`Outro` point.
*   **Gapless Playback**: Ensure 0ms latency between items.
*   **Voice Tracking**: Ability to play a voice file *over* the `Intro` of the next song (Duck volume of song).
*   **Audio Fingerprinting**: Research and implement fingerprinting for automatic track identification.

### 4.2 Automation Modes
*   **Live Assist**: Human driver. "Stops" at break points.
*   **Full Automation**: System picks next songs to fill time based on Logs.
*   **Manual**: Simple player (current state).

---

## 🖥️ Phase 5: On-Air User Interface

A simplified, high-contrast interface for the broadcast studio.

### 5.1 "On-Air" View (Live Assist)
*   **Triple Stack**: Visual representation of "Now Playing", "Next", "Next+1".
*   **Big Buttons**: massive START/STOP/NEXT buttons for touchscreen use.
*   **Cart Wall**: Grid of instant-play buttons for sound effects/beds.
*   **Clocks/Timers**: Countdown to end of song, Countdown to next hard-event (e.g., News at :00).

---

## 🔮 Future / Wishlist (Player & Hardware)

### Audio Processing & Output
- [ ] **DSP / VST Support**: Integration for VST plugins (compressor, limiter, EQ) on the master output.
- [ ] **Built-in Streaming Encoder**: Direct streaming to Icecast/Shoutcast servers (MP3/AAC).
- [ ] **Multiple Outputs**: Separate audio device configuration for "Cue" (Headphones) and "Air" (Speakers/Stream).

### Hardware & External Integration
- [ ] **GPIO / Fader Start**: Support for triggering playback via serial port or USB game controllers (simulating mixing console fader starts).
- [ ] **MIDI Control**: Support for MIDI surfaces to control faders/buttons physically.
- [ ] **Silence Detector**: Automatic email alert or failover mode if silence is detected for >10 seconds.
- [ ] **Voice Tracking Recorder**: A dedicated interface to record voice links while listening to the "tail" of the previous song and "intro" of the next.

---

## 🔗 Live Issue Reference
| Issue | Title | Status | Scope in Plan |
|-------|-------|--------|---------------|
| **[#7](https://github.com/PROdotes/Gosling2/issues/7)** | **Broadcast Automation** | ⏸️ Deferred | **Phase 4**. The core audio engine rewrite. |
