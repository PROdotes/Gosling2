---
type: task
id: T-75
title: Speculative Priming (Audio Pre-load)
status: todo
priority: medium
---

# T-75 Speculative Audio Priming

## Context
When the application restores a playlist (e.g., from a previous session) or loads a new list, the audio engine is often cold. Clicking "Play" results in a noticeable latency gap as the engine initializes and loads the file.

## Objective
Eliminate playback latency by "priming" (pre-loading) the first track in the active playlist immediately upon restoration.

## Requirements
1.  **Dual-Deck Initialization (Startup)**:
    *   **Deck A**: Pre-load Track #1 (Top of Playlist). State: `Paused/Ready`.
    *   **Deck B**: Pre-load Track #2 (On Deck). State: `Paused/Standby`.
    *   *Goal*: Instant start + Instant crossfade availability immediately after launch.

2.  **Just-in-Time Fade Priming**:
    *   Before executing any Crossfade or Next action, the system must verify the Target Deck has Media Loaded and Buffered.
    *   If not loaded, synchronously (or fast-async) load the target file *before* starting the volume ramp.
    *   This prevents "Silence Gaps" where the fader moves but audio hasn't started.

3.  **Continuous Readiness & Deck Cycling**:
    *   **Rotation Logic**: When mixing from Deck A -> Deck B (A stops, B plays):
        *   Deck A becomes "Free".
        *   System identifies Track #3 (Next-Next).
        *   System loads Track #3 into Deck A (Background).
        *   System updates "Next" pointer to target Deck A.
    *   *Result*: The user perceives an infinite stream, while under the hood we toggle A/B/A/B.
    *   *Worker*: Requires a non-blocking `on_fade_complete` trigger to perform the load safely.

4.  **Visual Feedback**:
    *   The "Play" button enable state should reflect Deck A readiness.
    *   The "Fade" button enable state should reflect Deck B readiness.

## Implementation Notes
*   **Previous Attempt**: Implemented in `src/presentation/views/main_window.py` around line 543.
*   **Logic**: `if restored_songs: self.playback_service.load(restored_songs[0].path)`
*   **Engine**: `VLCService` or `PlaybackService` needs to handle `load()` without `play()`. Currently `play(path)` does both. Might need `prime(path)` method.

## Verification
*   Start App.
*   Playlist restores 10 songs.
*   Click Play immediately.
*   **Result**: Instant sound. No "loading" spinner/lag.
