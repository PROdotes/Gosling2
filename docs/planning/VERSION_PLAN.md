---
tags:
  - type/strategy
  - status/active
---

# 🗺️ Gosling2 Version Plan

**Purpose**: High-level roadmap from legacy replacement to modern radio platform.  
**Last Updated**: 2025-12-23 (Vesper)

---

## 📊 Version Overview

| Version | Codename | Theme | Target |
|---------|----------|-------|--------|
| **0.1** | *The Replicant* | Legacy Parity | Do everything Gosling 1 could |
| **0.2** | *The Cleanup* | Technical Health | Refactor, test, stabilize |
| **1.0** | *The Broadcaster* | Modern Radio | Full cataloguing & automation |
| **2.0+** | *The Future* | Innovation | AI, integrations, "wow factor" |

---

## 🔹 Version 0.1 — *The Replicant*

**Goal**: Achieve feature parity with Gosling 1 (the legacy Java app).

**Success Criteria**:
- [ ] Import songs with full metadata extraction
- [ ] Organize files using legacy folder rules (`Z:\Songs\<Genre>\<Year>`)
- [ ] Read/write all ID3 tags Gosling 1 supported
- [ ] Detect duplicates (ISRC → Hash → Metadata tiered)
- [ ] Basic playback and navigation
- [ ] "Done" status flag (TKEY tag)
- [ ] Contributors (Artists, Groups, Aliases)
- [ ] Albums with artist disambiguation

**NOT in 0.1**:
- Advanced UI polish
- Playlist management
- Broadcast automation
- Undo/history (basic logging only)

**See**: [ROADMAP.md](ROADMAP.md) for detailed task breakdown.

---

## 🔹 Version 0.2 — *The Cleanup*

**Goal**: Pay down technical debt. Make the codebase maintainable.

**Success Criteria**:
- [ ] Test suite consolidated (target: ~20 files, not 68)
- [ ] Generic repository pattern for CRUD operations
- [ ] Logging system fully adopted across codebase
- [ ] Leviathans split (library_widget, yellberus, etc.)
- [ ] Documentation up to date

**Why a dedicated version?**
Most projects skip this and accumulate debt until collapse. Gosling2 won't be one of them.

**NOT in 0.2**:
- New features
- UI changes (except bug fixes)

---

## 🔹 Version 1.0 — *The Broadcaster*

**Goal**: A complete, modern radio cataloguing and automation platform.

**Success Criteria**:
- [ ] Side panel metadata editor
- [ ] Bulk editing capabilities
- [ ] Saved playlists
- [ ] Audit log with full history
- [ ] Undo/redo support
- [ ] Settings UI for user configuration
- [ ] Filter trees (genre/artist/album hierarchies)
- [ ] Broadcast automation basics (scheduling, export)
- [ ] Stable enough for daily production use

**Target Users**: Radio stations, music curators, serious collectors.

---

## 🔹 Version 2.0+ — *The Future*

**Goal**: Innovation. The "wouldn't it be cool if" features.

**Candidate Features**:
- [ ] **AI Playlist Generation** — Natural language → smart playlists ([T-33](docs/ideas/T-33_AI_PLAYLIST.md))
- [ ] **External Integrations** — Spotify API, MusicBrainz, Discogs
- [ ] **Advanced Analytics** — Play history insights, genre trends
- [ ] **Multi-user Support** — Permissions, concurrent editing
- [ ] **Cloud Sync** — Backup, multi-device access
- [ ] **Plugin System** — User-extensible functionality

**Philosophy**: 1.0 is for *users*. 2.0+ is for *delight*.

---

## 📈 Version Progression Logic

```
0.1 (Parity)     "Can it replace Gosling 1?"
      │
      ▼
0.2 (Health)     "Is it maintainable?"
      │
      ▼
1.0 (Complete)   "Is it a real product?"
      │
      ▼
2.0+ (Delight)   "Does it spark joy?"
```

---

## 🔗 Related Documents

| Document | Purpose |
|----------|---------|
| [ROADMAP.md](ROADMAP.md) | Detailed 0.1 task breakdown |
| [tasks.md](../tasks.md) | Task registry with priorities |
| [today.md](../today.md) | Daily execution plan |
