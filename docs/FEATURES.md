# Gosling2 Features Overview

**Gosling2** is an MP3 library manager and auto-player. This document provides a high-level overview of what's currently built in, designed for a quick read through the feature set and to help identify gaps or areas for enhancement.

---

## Core Capabilities

### Library Management
- **Upload & Ingest** — Batch upload MP3 and WAV files to build your music library
- **Duplicate Detection** — Automatically identifies files you've already ingested by comparing audio fingerprints
- **Soft Delete** — Remove songs without permanently erasing data; reactivate them later if needed
- **Folder Scanning** — Discover audio files across local directories, with optional recursive scanning

### Song Metadata
- **Core Fields** — Manage title, artist(s), year, BPM, ISRC codes, and notes for each track
- **Credits System** — Link performers, composers, producers, and other contributors to songs
- **Album Association** — Organize songs into albums with track and disc numbers
- **Tags/Genres** — Categorize and label songs with custom tags (genres, moods, eras, etc.)
- **Publishers** — Track labels, distributors, and copyright holders

### Audio Processing
- **MP3 Streaming** — Play back ingested tracks directly from the library
- **WAV Conversion** — Automatically convert WAV files to MP3 for unified library format
- **Waveform Visualization** — Display audio peaks for song scrubbing and timeline navigation

---

## Metadata Management

### Import & Enrichment
- **Spotify Integration** — Parse credits from Spotify album pages and import them into your library
- **File Inspection** — Compare database metadata against ID3 tags to spot discrepancies
- **ID3 Sync** — Write database metadata back to file tags for portability

### Tools & Utilities
- **Filename Parser** — Extract structured metadata from file names using templates
- **Credit Splitter** — Intelligently split artist credit strings into individual contributors
- **Publisher Splitter** — Similar to credit splitter, for isolating individual labels
- **Artist Lookup** — Check if an artist name already exists in your library before adding

### Search & Discovery
- **Case-Insensitive Search** — Find songs, albums, and artists regardless of capitalization
- **Diacritic-Insensitive Search** — Match "cafe" to "café", "Soren" to "Søren", etc.

---

## Album Management

### Album Operations
- **Album Creation** — Create albums and assign songs to them
- **Album Metadata** — Track album title, type (Single/EP/Album), and release year
- **Album Credits** — Add album-level credits (artists featured on multiple tracks, producers, etc.)
- **Album Publishers** — Link labels and distributors at the album level

### Sync Features
- **Sync from Song** — Automatically propagate metadata (year, performers, publishers) from a song to its album
- **Batch Updates** — Update multiple albums at once with consistent metadata

---

## Review & Approval Pipeline

### Processing Status
- **Reviewed** — Metadata is complete and verified
- **Needs Review** — Metadata is incomplete or flagged for attention
- **Pending Enrichment** — Waiting for metadata extraction or manual enrichment
- **Converting** — File format conversion in progress

### Review Blockers
The system identifies which fields must be completed before a song can be approved:
- Title
- Year
- Performer credits
- Composer credits
- Genre tags
- Publisher information
- Album assignment
- Valid duration

---

## Data Integrity & Audit

### Change Tracking
- **Audit Log** — Complete history of all metadata changes with timestamps
- **Soft Deletes** — Deleted records marked but preserved for audit trail
- **Cascading Operations** — Ensure referential integrity across linked records

---

## Technical Stack

- **Backend** — FastAPI-powered REST API (Python)
- **Frontend** — JavaScript/CSS web interface
- **Database** — SQLite with custom search optimization
- **Audio** — FFmpeg for format conversion
- **Server** — Runs locally (localhost:8000)

---

## What's Missing?

Areas to consider for future expansion:
- **Collaborative** — Multi-user support, shared libraries
- **Cloud Sync** — Backup and sync metadata to cloud storage
- **Smart Recommendations** — Suggest new music or related artists based on library
- **Playlists** — Create and manage dynamic/static playlists
- **Advanced Search** — Full-text search, faceted filtering, saved searches
- **Artwork** — Cover art management and display
- **Lyrics** — Store and search song lyrics
- **Statistics** — Library analytics, listening history, trends
- **Mobile** — Native mobile app or responsive mobile UI
- **API Webhooks** — Notifications for library changes
- **Batch Operations** — Bulk edit tools for metadata updates
- **Smart Renaming** — Auto-rename files based on metadata
- **Import Presets** — Save and reuse metadata extraction patterns

---

## Quick Start

1. **Upload** some MP3/WAV files to populate your library
2. **Review** ingested songs and fill in missing metadata
3. **Organize** into albums and add credits using Spotify integration or manual entry
4. **Search** for songs by title, artist, or tag
5. **Play** tracks directly from the app

