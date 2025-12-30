---
tags:
  # Per T-34 conventions
  - type/idea
  - status/future
  - domain/audio
  - domain/tags
  - layer/business
  - integration/api
  - integration/online
  - integration/musicbrainz
  - size/medium
  - risk/low
  - scope/post-1.0
links:
  - "[[IDEA_audio_fingerprinting]]"
  - "[[T-32 Pending Review Workflow]]"
  - "[[T-35 Music API Lookup]]"
---
# T-35: Music API Lookup

Fetch metadata from MusicBrainz, Discogs, Spotify API.

## Concept
- Search by artist, title, ISRC
- Auto-fill genre, year, album art
- Multiple API fallbacks

## APIs
- MusicBrainz (free, 1 req/sec rate limit)
- Discogs (free tier)
- Spotify (requires auth)

---

## Background Worker Pattern (Vesper Notes, 2025-12-23)

**Problem**: Bulk import of 400 songs + API lookup = 400+ seconds if synchronous.

**Solution**: Background worker queue.

### Workflow
1. **Import starts** → Songs tagged `System:Importing`
2. **Background worker** picks up songs from queue, calls MusicBrainz (1 req/sec)
3. **On MB success** → Store `MusicBrainzAlbumId`, change tag to `System:PendingReview`
4. **On MB failure** → Tag stays as `System:PendingReview` (manual lookup needed)
5. **User reviews** → Manually verifies/edits → Marks as `Done`

### Status Tag Progression
```
[Import]         System:Importing
    │
    ▼ (MB worker)
[API Done]       System:PendingReview
    │
    ▼ (User reviews)
[Complete]       Done (TKEY=true)
```

### Integration with Greatest Hits Fix
- If MusicBrainz returns Album ID → use MBID as definitive unique key
- If not → fall back to `(Title, AlbumArtist, Year)` matching
- This prevents rare edge cases (two "Best of 60s" compilations in same year)

