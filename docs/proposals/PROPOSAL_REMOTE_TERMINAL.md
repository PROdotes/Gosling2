# 🌐 PROPOSAL: Remote Terminal (Master/Slave Mode)

**Status:** Draft (Post-0.1, likely v0.3+)  
**Complexity:** High  
**Risk:** Network stability, audio latency, security

---

## 🎯 Problem Statement

When working remotely, I need to:
1. **See** the library exactly as it appears on the station PC (master)
2. **Hear** audio for genre identification without downloading entire files
3. **Edit** metadata that gets applied to the master's database
4. **Import** files from the master's download folder, not my local machine

Current workarounds (TeamViewer, RDP) are clunky and don't integrate with the workflow.

---

## 🏗️ Architecture Overview

```
┌─────────────────────┐           ┌─────────────────────┐
│   MASTER (Station)  │◄─────────►│   SLAVE (Remote)    │
│                     │  Network   │                     │
│  - Database         │           │  - UI Mirror        │
│  - Files            │           │  - Audio Playback   │
│  - Audio Output     │           │  - Local Input      │
└─────────────────────┘           └─────────────────────┘
        │                                   │
        │      ┌─────────────────┐          │
        └─────►│   Sync Protocol │◄─────────┘
               │   (WebSocket)   │
               └─────────────────┘
```

---

## 🔧 Components

### 1. Connection Layer
| Component | Technology | Notes |
|-----------|------------|-------|
| Protocol | WebSocket (wss://) | Bidirectional, low overhead |
| Auth | Token-based | Pre-shared secret or OAuth |
| Port | Configurable (default 9123) | May need NAT traversal |
| Encryption | TLS 1.3 | All traffic encrypted |

### 2. State Synchronization

**Master → Slave (Push):**
- Library state (song list, filter tree)
- Current selection
- Side panel data
- Playback position/status

**Slave → Master (Push):**
- User input (clicks, keypresses)
- Metadata edits
- Import requests

**Sync Strategy:**
- Initial: Full state snapshot
- Ongoing: Delta updates (JSON patches)
- Conflict: Master always wins (slave is "thin client")

### 3. Audio Streaming

| Option | Latency | Quality | Bandwidth |
|--------|---------|---------|-----------|
| **Opus (recommended)** | ~50ms | Good | ~64-128 kbps |
| MP3 stream | ~200ms | Good | ~128-320 kbps |
| Raw PCM | ~20ms | Perfect | ~1.4 Mbps |

**Implementation:**
```python
# Master: Capture audio output
audio_capture = AudioLoopback()  # PyAudio or sounddevice
compressed = opus_encode(audio_capture.read())
websocket.send_binary(compressed)

# Slave: Playback
raw_audio = opus_decode(websocket.recv())
audio_output.play(raw_audio)
```

**Considerations:**
- Use adaptive bitrate based on connection quality
- Buffer 100-200ms to handle jitter
- Mute option (don't stream if just editing metadata)

### 4. File System Access

**Use Case:** Import song from master's Downloads folder

**Flow:**
```
Slave: "Show me /Downloads/*.mp3"
  │
  ▼
Master: [list of files with thumbnails/metadata preview]
  │
  ▼
Slave: "Import song_x.mp3"
  │
  ▼
Master: [runs import pipeline locally, syncs result to slave]
```

**Security:**
- Whitelist accessible directories (no arbitrary file access)
- Read-only by default, import = copy to library folder
- No delete operations via remote

---

## 🎨 UI Modes

### Mode A: Full Mirror
- Slave sees exactly what master sees
- All interactions forwarded to master
- Like remote desktop but integrated

### Mode B: Independent View (Future)
- Slave has own filter/selection state
- Edits still sync to master
- Better for "I'm working on a specific task while station runs"

---

## 📋 Implementation Phases

### Phase 1: Basic Connection (~8h)
- [ ] WebSocket server in master
- [ ] WebSocket client in slave
- [ ] Authentication handshake
- [ ] Connection status indicator in UI

### Phase 2: State Sync (~12h)
- [ ] Serialize library state to JSON
- [ ] Delta updates for efficiency
- [ ] Forward user input events
- [ ] Sync selection/filter state

### Phase 3: Audio Streaming (~10h)
- [ ] Audio capture on master (loopback)
- [ ] Opus encoding/decoding
- [ ] Playback on slave with buffering
- [ ] Volume/mute controls

### Phase 4: File Access (~6h)
- [ ] Directory listing over WebSocket
- [ ] Metadata preview (read ID3 remotely)
- [ ] Trigger import on master
- [ ] Progress feedback to slave

### Phase 5: Hardening (~8h)
- [ ] Reconnection logic
- [ ] Graceful degradation (audio drops, UI continues)
- [ ] Logging and diagnostics
- [ ] NAT traversal (STUN/TURN?) or VPN recommendation

---

## ⚠️ Known Challenges

| Challenge | Mitigation |
|-----------|------------|
| **NAT/Firewall** | Use relay server (see below) |
| **Audio latency** | Opus + small buffer; accept ~100ms delay |
| **Bandwidth** | Audio is main cost (~100kbps); compress state updates |
| **Security** | TLS + auth token; whitelist directories |
| **Conflict resolution** | Master wins; slave is display-only |
| **Testing** | Need two machines; mock network layer for unit tests |

---

## 🔄 Relay Server Architecture (Recommended)

Instead of exposing the master directly, use the **24/7 streaming PC** as a relay:

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│    MASTER    │◄───────►│    RELAY     │◄───────►│    SLAVE     │
│  (Station)   │   LAN   │  (24/7 PC)   │   WAN   │   (Remote)   │
└──────────────┘         └──────────────┘         └──────────────┘
                              │
                    gosling.dyndns.org:9123
```

### Benefits
- Only ONE port to forward (on relay)
- Master doesn't need direct internet exposure
- Relay can buffer audio for jitter smoothing
- DynDNS handles dynamic IP
- Can log/record sessions

### Service Discovery

When slave connects, relay scans the LAN for running masters:

```
1. Slave connects to gosling.dyndns.org:9123
2. Relay scans 192.168.1.10-20 for Gosling instances
3. Masters respond with: { "name": "STUDIO-PC", "version": "0.3.0" }
4. Relay presents list to slave: "Pick a master to connect to"
5. Slave selects → Relay bridges the connection
```

### Relay Modes

| Mode | Description | Complexity |
|------|-------------|------------|
| **Dumb Pipe** | Just forward WebSocket frames | Low |
| **Smart Proxy** | Auth, logging, rate limiting | Medium |
| **Full Relay** | Audio transcoding, caching | High |

**Recommendation:** Start with Dumb Pipe, add smarts as needed.

### DynDNS Setup
- Use free service: DuckDNS, No-IP, FreeDNS
- Relay runs update script on IP change
- Slave config: `gosling.mystation.duckdns.org:9123`

---

## 🔮 Future Extensions

- **Multi-slave:** Multiple remotes connected to one master
- **Mobile client:** Stripped-down iOS/Android viewer
- **Cloud relay:** Avoid NAT issues via relay server (adds latency)
- **Recording:** Stream to slave = also record session

---

## 📚 Prior Art

| Tool | What It Does | Applicable? |
|------|--------------|-------------|
| Parsec | Low-latency game streaming | Audio/video approach |
| Syncthing | File sync | State sync patterns |
| Teamspeak | Real-time audio | Opus streaming |
| VS Code Remote | Remote dev | WebSocket RPC patterns |

---

## 🎯 MVP Definition (Snow Day Mode)

> **Scope:** "I'm snowed in, let me remote in and process the song backlog."
> **Not Scope:** Cue points, precise timing, professional monitoring — do that on-site.

**What you need remotely:**
- See library, filter, search ✅
- Edit metadata (Artist, Genre, Publisher, Composer) ✅
- Quick audio preview (low quality OK — just identify genre/language) ✅
- Mark as DONE ✅
- Import from master's Downloads folder ✅

**What you DON'T need remotely:**
- Real-time waveform rendering
- Precise cue marker editing
- High-fidelity audio monitoring
- Live crossfade preview

### Simplest Implementation (REST + Web UI)

Skip the fancy WebSocket sync. Start with:

```
Master: Flask API (50 lines)
├── GET  /api/songs          → Library list
├── GET  /api/songs/{id}     → Song details
├── PUT  /api/songs/{id}     → Update metadata
├── GET  /api/preview/{id}   → 15-sec audio clip (32kbps, base64)
└── POST /api/import         → Trigger import from Downloads

Slave: Web browser
├── Simple React/Vue dashboard
├── Audio preview = <audio src="data:audio/mp3;base64,...">
└── Form fields for metadata editing
```

**Effort:** ~8-12 hours for basic functionality

Later, if you need better UX, upgrade to full client with WebSocket sync.

### Audio Preview (Keep It Stupid Simple)

| Approach | Quality | Bandwidth | Complexity |
|----------|---------|-----------|------------|
| **Base64 clip in JSON** | 32kbps, 15sec | ~60KB | Trivial |
| HTTP chunked stream | Variable | Stream | Low |
| WebSocket Opus | Real-time | ~64kbps | Medium |

For "is this Zabavna or Narodna?" → **Base64 clip wins**. Upgrade when needed.

---

## 📝 Notes

- This is essentially building a custom "remote desktop" tuned for Gosling
- Alternative: Just use Parsec/RDP and accept the UX compromise
- But native integration = better shortcuts, no screen sharing lag, purpose-built

**Estimated Total:** ~44 hours (v0.3+)
