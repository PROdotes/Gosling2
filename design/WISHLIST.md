# Feature Ideas — Future / Backlog

> **Purpose:** Capture ideas for radio automation features that are NOT planned for current development. This prevents feature creep while ensuring good ideas aren't forgotten.

---

## Scheduling & Automation
- [ ] **Clock Templates** — Hour templates defining song/jingle/break patterns
- [ ] **Schedule Generator** — Auto-generate daily playlists from clocks
- [ ] **Rotation Rules** — "Don't repeat artist within 60 minutes"
- [ ] **Last Played Tracking** — Track when each song/artist last aired
- [ ] **Separation Rules** — "Don't play Pepsi after Coke ad"
- [ ] **Dayparting** — Different rules for morning/afternoon/night

## Audio Processing
- [ ] **File Format Conversion** — Convert WAV→MP3/AAC on import, quality presets
- [ ] **VST/DSP Support** — Compressor, limiter, EQ on master output
- [ ] **Silence Detection** — Alert if silence > 10 seconds
- [ ] **Audio Fingerprinting** — Auto-identify unknown tracks
- [ ] **Loudness Normalization** — EBU R128 / ReplayGain

## Streaming & Output
- [ ] **Built-in Encoder** — Stream to Icecast/Shoutcast
- [ ] **Multiple Outputs** — Separate "Cue" and "Air" audio devices
- [ ] **Now Playing Push** — HTTP POST to website, RDS encoder

## Hardware Integration
- [ ] **GPIO / Fader Start** — Trigger from physical console
- [ ] **MIDI Control** — Map MIDI surfaces to controls
- [ ] **Silence Failover** — Auto-switch to backup source

## Remote Control
- [ ] **Remote App Connection** — Log into app from remote device
- [ ] **Mirror View** — See what the main app sees (library, playlist, now playing)
- [ ] **Remote Audio Monitor** — Hear what's playing (stream output to remote)
- [ ] **Remote Control** — Start/stop/skip from remote device
- [ ] **Multi-User** — Multiple remotes can connect simultaneously

## Voice Tracking
- [ ] **Voice Recorder** — Record links while hearing intro/outro
- [ ] **Ducking** — Auto-lower music when voice detected

## Hooks & Teasers
- [ ] **Teaser Mode** — "Coming up next" plays HookIn→HookOut segment
- [ ] **Preview Hook** — Quick-listen button in library to hear just the hook
- [ ] **Auto-Teaser Generator** — Stitch hooks together for "This hour on..." promos

## Auto-Tag Management
- [ ] **Rule Graph Visualization** — Visual diagram of auto-tag rules and cascades
- [ ] **Cycle Detection Warning** — UI alerts when rules create infinite loops
- [ ] **Rule Testing** — Preview what tags a song would get before saving

## Traffic & Billing
- [ ] **Commercial Scheduler** — Ensure ad separation, proof-of-play
- [ ] **Contract Management** — Client, campaign, flight dates
- [ ] **Affidavit Generator** — Proof of airing reports

## Reporting
- [x] **As-Run Log** — What actually played (royalty reporting) → *Moved to tasks.md as PlayHistory*
- [ ] **Statistics Dashboard** — Most played, rotation analysis
- [ ] **Export to ASCAP/BMI** — Royalty reporting formats

## Metadata & Cloud
- [ ] **Music API Lookup** — Fetch metadata from MusicBrainz, Discogs, Spotify API
- [ ] **Auto-fill on Import** — Check ISRC/fingerprint against online DBs
- [ ] **Gosling Cloud Sync** — Shared metadata database for app users
- [ ] **Crowd-sourced Data** — Upload/download metadata by song ID

---

*Last updated: Dec 18, 2024*
