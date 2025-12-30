---
tags:
  - layer/data
  - domain/database
  - domain/audio
  - status/future
  - type/feature
  - size/small
  - value/high
  - risk/low
  - scope/local
  - skill/sql
links:
  - "[[DATABASE]]"
  - "[[IDEA_rotation_rules]]"
---
# Last Played Tracking

Track when each song/artist last aired for rotation logic.

## Concept
- Store last play timestamp per song
- Store last play timestamp per artist
- Query: "Songs not played in last 4 hours"

## Related
- [[IDEA_rotation_rules]]
- [[PROPOSAL_TRANSACTION_LOG]] (PlayHistory)
