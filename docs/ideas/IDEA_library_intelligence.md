# 📚 IDEA: Library Intelligence & Gap Analysis

**Status:** Future (Post-0.1)  
**Complexity:** Medium-High  
**Value:** Very High — saves hours of manual chart-chasing and prevents "we don't have that?!" moments

---

## Problems This Solves

1. **Chart tracking is manual** — Hours spent comparing Spotify Top 50 against library
2. **Gap discovery is forgotten** — "We only have 2 Blondie songs?!" → forget in 5 minutes
3. **Listener requests reveal gaps** — "Can you play Karma Chameleon?" → "Uh... we don't have it"
4. **Artist aliases break search** — "Boy George" finds nothing, but "Culture Club" has the song

---

## Features

### 1. Chart Comparison Dashboard

Automatically fetch and compare against popular charts:

```
┌─────────────────────────────────────────────────┐
│  SPOTIFY TOP 50 GLOBAL — This Week              │
├─────────────────────────────────────────────────┤
│  ✓ 34 songs — In Library                        │
│  ✗ 16 songs — Missing                           │
│                                                 │
│  Missing:                                       │
│  • Dua Lipa - Houdini          [+ Wishlist]     │
│  • Beyoncé - Texas Hold 'Em    [+ Wishlist]     │
│  • ...                                          │
└─────────────────────────────────────────────────┘
```

**Sources:**
- Spotify Top 50 (Global, Europe, Croatia)
- Billboard Hot 100
- ZAMP Top Lista (if accessible)
- Custom chart URLs

**API:** Spotify Web API (free, read-only for public playlists)

### 2. Artist Coverage Report

For any artist, show what you have vs. what exists:

```
┌─────────────────────────────────────────────────┐
│  ARTIST: Queen                                  │
├─────────────────────────────────────────────────┤
│  In Library: 12 songs                           │
│  Known Hits: 25+ (from MusicBrainz)             │
│                                                 │
│  Missing Essentials:                            │
│  • I Want It All (1989)                         │
│  • Radio Ga Ga (1984)                           │
│  • Somebody to Love (1976)                      │
│                                                 │
│  [View Full Discography] [Add All to Wishlist]  │
└─────────────────────────────────────────────────┘
```

**Source:** MusicBrainz artist discography

### 3. Library Wishlist

Quick capture of "we need this" thoughts before you forget:

```python
# Ctrl+W anywhere in app
def add_to_wishlist():
    text = quick_input("What do we need?")
    wishlist.add(text, timestamp=now(), source="manual")
```

**Wishlist entries from:**
- Manual entry (keyboard shortcut)
- Chart comparison ("add missing to wishlist")
- Listener request log (see below)
- Artist gap report

### 4. Listener Request Log

When a listener calls in:

```
┌─────────────────────────────────────────────────┐
│  LISTENER REQUEST                               │
├─────────────────────────────────────────────────┤
│  Request: "Boy George - Karma Chameleon"        │
│                                                 │
│  Search Result:                                 │
│  ✗ No direct match for "Boy George"             │
│  ✓ Found via alias: Culture Club → Karma Cham.  │
│                                                 │
│  [Play Now] [Not in Library — Add to Wishlist]  │
└─────────────────────────────────────────────────┘
```

**Features:**
- Search includes artist aliases (Boy George → Culture Club)
- Log requests even if not fulfilled
- Weekly report: "Listeners asked for these 5 songs we don't have"

### 5. Smart Alias Search

Enhance search to always check aliases:

```python
def search_songs(query: str) -> list[Song]:
    # Direct match
    results = db.search(title=query, artist=query)
    
    # Alias match
    for alias in contributor_repo.find_aliases(query):
        results += db.search(artist=alias.primary_artist.name)
    
    # MusicBrainz fallback for unknown aliases
    if not results:
        mb_artist = musicbrainz.search_artist(query)
        if mb_artist and mb_artist.aliases:
            for alias in mb_artist.aliases:
                results += db.search(artist=alias)
    
    return dedupe(results)
```

---

## Implementation Priority

| Feature | Effort | Value | Priority |
|---------|--------|-------|----------|
| Wishlist (Ctrl+W) | 2h | High | ⭐ Do first |
| Smart Alias Search | 4h | High | ⭐ Do first |
| Listener Request Log | 4h | Medium | Second |
| Artist Coverage Report | 8h | Medium | Third |
| Chart Comparison | 12h | High | Last (API work) |

---

## Data Sources

| Source | Data | Access |
|--------|------|--------|
| Spotify API | Charts, playlists | Free (OAuth) |
| MusicBrainz | Discographies, aliases | Free (rate-limited) |
| Discogs | Album info, release years | Free (API key) |
| ZAMP | Croatian charts | Unknown (scrape?) |

---

## User Stories

> "I'm processing songs and think 'why do we only have 2 Blondie songs?' — I hit Ctrl+W, type 'More Blondie', and get back to work. Next month I review the wishlist and actually do something about it."

> "A listener calls wanting Karma Chameleon by Boy George. I search 'Boy George', the alias system finds Culture Club, I play it. If we didn't have it, one click adds it to wishlist."

> "Every Monday I open the Chart dashboard. It shows we're missing 12 of this week's Top 50. I add the ones that fit our format to the wishlist, ignore the rest."

---

## Related Ideas

- [IDEA_music_api_lookup.md](IDEA_music_api_lookup.md) — MusicBrainz/Discogs integration
- [IDEA_crowd_sourced_data.md](IDEA_crowd_sourced_data.md) — Community metadata
- [IDEA_statistics_dashboard.md](IDEA_statistics_dashboard.md) — Library analytics
