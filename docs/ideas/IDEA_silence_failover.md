---
tags:
  - layer/core
  - domain/audio
  - status/future
  - type/feature
  - size/medium
  - value/high
  - risk/low
  - scope/local
  - skill/python
links:
  - "[[IDEA_silence_detection]]"
  - "[[PROPOSAL_BROADCAST_AUTOMATION]]"
---
# Silence Failover

Auto-switch to backup source if main audio fails.

## Concept
- Monitor main output for silence
- If silence > X seconds, switch to backup
- Backup sources: playlist, stream, pre-recorded audio

## Related
- [[IDEA_silence_detection]]
