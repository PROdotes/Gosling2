# Gosling2 - Radio Automation Transition Plan

## 📋 Overview
This document outlines the roadmap for transforming **Gosling2** from a personal MP3 library manager into a professional **Radio Automation System**.
This shift moves the focus from "cataloging and playing" to "scheduling, precise timing, and unattended broadcasting".

---

## 🏗️ Phase 1: Core Architecture & Database (Issue #4)

The foundation must support radio-specific metadata and scheduling structures.
**Source: [Issue #4 - database](https://github.com/PROdotes/Gosling2/issues/4)**

### 1.1 Database Schema Updates
We need to extend the schema to support broadcast timing and scheduling.
*   **Update `Files` Table**:
    *   Add `CueIn`, `CueOut` (trim silence).
    *   Add `Intro` (time until vocals start).
    *   Add `HookIn`, `HookOut` (for "coming up next" previews).
    *   Add `SegType` (Next, Stop, Overlap).
    *   Add `Type` (Song, Jingle, Spot, VoiceTrack, Bed).
*   **New Tables (as per Issue #4)**:
    *   `AutomationPhases`: Define scheduling rules (e.g., Morning Drive, Night Shift).
    *   `PhaseRules`: Specific rules for phases.
    *   `PlaylistQueue`: Persistent queue management.
    *   `Tracklist`: Support for multi-album/compilation tracking.
    *   `Clocks`: Definitions of hour templates.
    *   `PlayLogs`: "As-Run" logs for royalty reporting.

### 1.2 Model & Repository Updates
*   Update `Song` dataclass to include new timing and type fields.
*   Update `SongRepository` to handle the new schema fields and relations.
*   **New Repositories**: `ClockRepository`, `ScheduleRepository`, `PhaseRepository`.

---

## 🎧 Phase 2: Audio Engine Overhaul (Issue #7)

The current "Ping-Pong" player is good, but radio needs "Segue" logic, not just crossfading at end of track.
**Source: [Issue #7 - Broadcast Automation & Timing Logic](https://github.com/PROdotes/Gosling2/issues/7)**

### 2.1 Precision Playback
*   **Segue Logic**: The `PlaybackService` must trigger the next event based on the current song's `NextCue`/`Outro` point.
*   **Gapless Playback**: Ensure 0ms latency between items.
*   **Audio Fingerprinting**: Research and implement fingerprinting for automatic track identification (as mentioned in Issue #7).

### 2.2 Automation Modes
*   **Live Assist**: Human driver. Stops at break points.
*   **Full Automation**: System picks next songs to fill time based on `AutomationPhases`.
*   **Manual**: Simple player (current state).

---

## 🖥️ Phase 3: User Interface (Issues #3, #6, #8)

The interface needs different modes for different tasks.

### 3.1 "On-Air" View (Live Assist)
A simplified, high-contrast interface for the studio.
*   **Triple Stack**: "Now Playing", "Next", "Next+1".
*   **Big Buttons**: massive START/STOP/NEXT.
*   **Cart Wall**: Grid of instant-play buttons.
*   **Clocks/Timers**: Countdown to end of song, Countdown to next hard-event.

### 3.2 Library Manager (Current View)
Refine the current view for "Back office" work.
*   **Side-Panel Editor (Issue #3)**: Implement a "Quick Edit" panel to set Cue Points/Intro times visually.
*   **Library View Modes (Issue #6)**: Implement distinct views for Songs, Jingles, and Spots.
*   **Drag & Drop (Issue #8)**: Finish implementing drag & drop import for easier library management.

### 3.3 Log Editor/Scheduler
*   **Clock Creator**: Visual editor to build hour templates using `AutomationPhases`.
*   **Log View**: Grid view of the daily schedule managed via `PlaylistQueue`.

---

## 🚀 Roadmap Summary

| Phase | Task | Description |
|-------|------|-------------|
| **1** | **Database Migration** | Implement `AutomationPhases`, `PlaylistQueue`, and updated `Files`. |
| **2** | **Audio Engine** | Implement segue points, mix logic, and fingerprinting (Issue #7). |
| **3** | **On-Air UI** | Create Live Assist view and improved Library management. |
| **4** | **Scheduler** | Implement Clocks and Log generation. |
| **5** | **Cart Wall** | Add instant-play buttons widget. |

---

## � Issue Tracker Integration (Consolidated)

This plan integrates requirements from the following active GitHub issues. This document serves as the implementation source of truth.

| Issue | Title | Status | Scope in Plan |
|-------|-------|--------|---------------|
| **[#7](https://github.com/PROdotes/Gosling2/issues/7)** | **Broadcast Automation** | 🏃 Active | **Parent Issue**. Phase 2 (Audio Engine), Phase 4 (Scheduler). Fingerprinting. |
| **[#4](https://github.com/PROdotes/Gosling2/issues/4)** | **Database Schema** | 🏗️ In Progress | **Phase 1**. Defines `AutomationPhases`, `PlaylistQueue`, `Tracklist`. |
| **[#3](https://github.com/PROdotes/Gosling2/issues/3)** | **Side-Panel Editor** | 📅 Planned | **Phase 3.2**. Spec for the "Quick Edit" interface. |
| **[#6](https://github.com/PROdotes/Gosling2/issues/6)** | **Library View Modes** | 📅 Planned | **Phase 3.2**. Requirement for Song/Jingle/Spot separation. |
| **[#8](https://github.com/PROdotes/Gosling2/issues/8)** | **Library Drag & Drop** | 📅 Planned | **Phase 3.2**. UX requirement for library management. |

*Note: Future/Wishlist features not yet tracked in GitHub (VSTs, Hardware) are maintained in `future_roadmap.md`.*
