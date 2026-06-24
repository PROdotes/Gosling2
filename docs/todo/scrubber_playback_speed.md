# Scrubber Playback Speed

## Goal
Let the scrubber play faster (e.g. 2x) for quicker review listening.

## Scope
Frontend only. The scrubber uses a vanilla `<audio>` element (`scrubber-audio` in
`src/static/js/dashboard/components/scrubber_modal.js`), so the audio side is just
`audio.playbackRate`. No backend, no waveform changes. Modern browsers default
`preservesPitch = true`, so faster playback does not raise pitch.

## Work (current direction)
Discrete speed buttons in the modal (e.g. `1x / 1.5x / 2x`), each also bound to a number
key: `1` / `2` / `3`.

1. Render the speed buttons in the scrubber modal.
2. Click handler sets `audio.playbackRate` and marks the active button.
3. Bind keys `1` / `2` / `3` in the existing `handleScrubberKeydown`.

### Tap vs hold (open decision)
Two interaction models for the keys/buttons:
- **Tap to set** — pressing `2` switches to that speed until you pick another. Simple
  state, persists.
- **Hold for momentary** — speed applies only while the key is held (keydown sets it,
  keyup reverts to 1x). Good for a quick skim, snaps back on release. Needs a keyup
  listener and tracking the held key.

Could also support both (tap sets, hold-then-release reverts). Decide before building.

## Gotcha
`playbackRate` resets to `1` whenever `audio.src` changes (each new song). To keep the
speed sticky across tracks, also set `audio.defaultPlaybackRate` and/or re-apply the
chosen rate in the existing `loadedmetadata` listener.

## Open decisions
- Cycle button vs. plain 2x toggle.
- Sticky across songs vs. reset to 1x per track.
- (Optional) expose default speed as a runtime setting via `config_service` Settings.

Estimate: ~15-20 lines, small.
