---
tags:
  - layer/core
  - domain/audio
  - status/future
  - type/feature
  - size/medium
  - value/medium
  - risk/medium
  - scope/local
  - skill/python
  - needs/hardware
links:
  - "[[PROPOSAL_ONAIR_UI]]"
---
# MIDI Control

Map MIDI surfaces to app controls.

## Concept
- Connect MIDI controller (Novation, Akai, etc.)
- Map buttons to play/stop/next
- Map faders to volume controls

## Requirements
- MIDI library (pygame.midi, mido)
- USB MIDI device
