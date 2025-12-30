---
tags:
  - id3
  - metadata
  - portability
status: planned
priority: medium
---

# T-04: ID3 Portable Metadata Sync

## Core Principle
> **The MP3 file IS the portable database.**

When an MP3 is transferred between radio stations, all metadata travels with it via ID3 tags. The receiving Gosling 2 auto-populates its database from the embedded tags.

## Implementation Checklist

### Write Direction (DB → ID3)
- [ ] Implement `MetadataService.write_tags(song: Song)`
- [ ] Map Song fields to ID3 frames (use `FieldDef.id3_frame`)
- [ ] Preserve unmanaged frames (don't clobber custom tags)
- [ ] Handle ID3v1 vs ID3v2 properly (prefer v2)

### Read Direction (ID3 → DB)
- [ ] On import, auto-populate Song from ID3 tags
- [ ] Handle comma-separated list fields (TPE1 → performers)
- [ ] Detect and log missing mappings

### Field Classification
| Type | Examples | Sync |
|------|----------|------|
| Portable | Artists, Title, Year, ISRC, BPM, Composers | ✅ |
| Local-only | source_id, is_done, play_count | ❌ |

### Validation
- [ ] Yellberus yells if portable field lacks `id3_frame`
- [ ] Test: Round-trip (write → read → compare)

## See Also
- [TODO_METADATA_WRITE_COMPLETE.md](./TODO_METADATA_WRITE_COMPLETE.md)
- [T-02_field_registry.md](./T-02_field_registry.md)

## Future Work
- [ ] **Review Impact** — Spend time thinking about how this affects existing tasks and implemented features
