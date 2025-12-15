# Gosling2 - Database & Data Management Plan (Active)

## 📋 Overview
This document outlines the **Immediate Active Phase** of the Radio Automation transition.
**Focus**: Database Schema, Data Entry, Library Management, and Scheduling Logic.
**Goal**: Build the data structure and back-office tools required for automation.

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
*   **New Tables**:
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

## 🖥️ Phase 2: Library & Data Management UI (Issues #3, #6, #8)

Refine the current view for "Back office" work.

### 2.1 Side-Panel Editor (Issue #3)
Implement a "Quick Edit" panel to set Cue Points/Intro times visually.
*   **Requirements**: Waveform visualization (optional MVP), sliders for `Intro` / `Outro` points, `Type` selector.

### 2.2 Library View Modes (Issue #6)
Implement distinct views for different audio types.
*   **Requirements**: Filter tabs or specific views for Songs, Jingles, Spots, Beds.

### 2.3 Drag & Drop Import (Issue #8)
Finish implementing drag & drop import for easier library management.

---

## 📅 Phase 3: Scheduler & Log Editor (New Features)

Tools to create the daily playlist data.

### 3.1 Clock Creator
Visual editor to build hour templates using `AutomationPhases`.
*   **Data**: CRUD operations on the `Clocks` table.

### 3.2 Log Editor
Grid view of the daily schedule managed via `PlaylistQueue`.
*   **Data**: View/Edit the generated `Schedules` table.

---

## 🔮 Future / Wishlist (Database)
*   **Traffic/Billing Generator**: Specialized scheduler for commercials to ensure separation (e.g., don't play two car ads back-to-back) and proof-of-play generation.
*   **Metadata Push**: HTTP GET/POST callbacks to push "Now Playing" data to websites/RDS.

---

## 🔗 Issue Tracker Integration

| Issue | Title | Status | Scope in Plan |
|-------|-------|--------|---------------|
| **[#4](https://github.com/PROdotes/Gosling2/issues/4)** | **Database Schema** | 🏗️ In Progress | **Phase 1**. Defines `AutomationPhases`, `PlaylistQueue`. |
| **[#3](https://github.com/PROdotes/Gosling2/issues/3)** | **Side-Panel Editor** | 📅 Planned | **Phase 2.1**. Spec for the "Quick Edit" interface. |
| **[#6](https://github.com/PROdotes/Gosling2/issues/6)** | **Library View Modes** | 📅 Planned | **Phase 2.2**. Requirement for Type separation. |
| **[#8](https://github.com/PROdotes/Gosling2/issues/8)** | **Library Drag & Drop** | 📅 Planned | **Phase 2.3**. UX requirement. |
