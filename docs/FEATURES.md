# Gosling2 Features Overview

**Gosling2** is an MP3 library manager and auto-player. This document provides a high-level overview of what's currently built in, designed for a quick read through the feature set and to help identify gaps or areas for enhancement.

---

## Table of Contents

1. [Core Capabilities](#core-capabilities)
2. [Metadata Management](#metadata-management)
3. [Artist & Identity Management](#artist--identity-management)
4. [Album Management](#album-management)
5. [Search & Discovery](#search--discovery)
6. [Audio & Playback](#audio--playback)
7. [Review & Approval Pipeline](#review--approval-pipeline)
8. [Staging & File Management](#staging--file-management)
9. [Data Integrity & Audit](#data-integrity--audit)
10. [Technical Stack](#technical-stack)
11. [What's Missing?](#whats-missing)

---

## Core Capabilities

### Library Management
- **Upload & Ingest** — Batch upload MP3 and WAV files to build your music library
- **Duplicate Detection** — Automatically identifies files you've already ingested by comparing audio fingerprints
- **Smart Duplicate Finding** — Find songs that share the same title and performer(s) across your library
- **Soft Delete** — Remove songs, albums, tags, and publishers without permanently erasing data; reactivate later if needed
- **Folder Scanning** — Discover audio files across local directories, with optional recursive scanning
- **File Hash Verification** — SHA256-based fingerprinting ensures reliable duplicate and conflict detection

### Song Metadata
- **Core Fields** — Manage title, artist(s), year, BPM, ISRC codes, and notes for each track
- **Credits System** — Link performers, composers, producers, and other contributors to songs with role assignments
- **Album Association** — Organize songs into albums with track and disc numbers
- **Tags/Genres** — Categorize and label songs with custom tags (genres, moods, eras, etc.) and hierarchical categories
- **Publishers** — Track labels, distributors, and copyright holders with hierarchical publisher relationships
- **Scalar Field Validation** — Year, BPM, ISRC, track/disc numbers all validated against configurable rules

---

## Metadata Management

### Import & Enrichment
- **Spotify Integration** — Parse credits from Spotify album pages and import them into your library
- **File Inspection** — Compare database metadata against ID3 tags to spot discrepancies
- **ID3 Sync** — Write database metadata back to file tags for portability
- **Web Search** — Generate search URLs for songs on Spotify, YouTube, or other configurable search engines

### Tools & Utilities
- **Filename Parser** — Extract structured metadata from file names using templates; preview before applying
- **Batch Filename Parsing** — Apply extracted metadata from multiple filenames to the database in one operation
- **Credit Splitter** — Intelligently split artist credit strings into individual contributors
- **Publisher Splitter** — Split publisher credit strings into individual labels
- **Artist Lookup** — Check if an artist name already exists in your library before adding
- **Text Casing** — Format text to title case or sentence case (utility for metadata cleanup)

### Search & Discovery
- **Case-Insensitive Search** — Find songs, albums, artists, and publishers regardless of capitalization
- **Diacritic-Insensitive Search** — Match "cafe" to "café", "Soren" to "Søren", etc.
- **Advanced Filtering** — Filter by:
  - Artists (performers)
  - Contributors (composers, producers, etc.)
  - Years and decades
  - Genres/tags
  - Albums
  - Publishers
  - Processing status
  - Original file availability
  - Live-only mode
- **Deep Search** — Full-resolution search across all metadata for comprehensive discovery

---

## Artist & Identity Management

### Identity System
- **Create & Manage Identities** — Track artists, producers, composers as first-class entities
- **Artist Aliases** — Multiple display names for the same artist (e.g., stage name, legal name, variations)
- **Artist Types** — Distinguish between individual artists and groups
- **Group Memberships** — Link member artists to band/group identities
- **Identity Trees** — View complete hierarchies including all aliases and group memberships
- **Merge Identities** — Consolidate duplicate artist records (with confirmation)

### Artist Discovery
- **Search All Identities** — Find artists by name, alias, or legal name
- **Artist Detail Views** — See all songs, albums, and credits for an artist across all their aliases
- **Exclude Groups Option** — Filter searches to show only individual artists (or vice versa)

---

## Album Management

### Album Operations
- **Album Creation** — Create albums and assign songs to them
- **Album Metadata** — Track album title, type (Single/EP/Album), and release year
- **Album Credits** — Add album-level credits (artists featured on multiple tracks, producers, etc.)
- **Album Publishers** — Link labels and distributors at the album level
- **Track Positioning** — Set track numbers and disc numbers for precise album organization
- **Primary Album** — Designate which album is "canonical" for a song (when linked to multiple)

### Sync & Automation
- **Sync from Song** — Automatically propagate metadata (year, performers, publishers) from a song to its album
- **Bidirectional Album-Song Sync** — Keep album and track metadata in sync

### Album Cleanup
- **Delete Unlinked Albums** — Remove albums with no associated songs (with safety confirmation)
- **Album Detail Views** — See complete album information including all tracks, credits, and publishers

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

## Staging & File Management

### Upload Workflow
- **Streaming Upload** — Real-time progress feedback during multi-file uploads
- **File Format Filtering** — Only `.mp3` and `.wav` files are accepted; others silently ignored
- **Staged File Tracking** — Uploaded files temporarily stored in staging area before processing
- **Ingestion Status Reporting** — Track upload, conversion, and ingestion progress with status badges

### WAV Management
- **Auto-Conversion** — Automatically convert WAV files to MP3 for unified library format (configurable)
- **Pending Conversion Queue** — View and manage WAV files awaiting conversion
- **Manual Conversion Control** — Convert on-demand when auto-conversion is disabled

### File Cleanup
- **Original File Preservation** — Optionally keep original source files separate from library files
- **Original File Deletion** — Safely delete original files after successful ingestion (with confirmation)
- **Staging Orphan Cleanup** — Remove orphaned files from staging directory that aren't tracked in DB
- **Ingestion Collision Check** — Dry-run check before ingesting to detect duplicates or conflicts

### Conflict Resolution
- **Duplicate Detection** — Identify when a file matches an already-active record
- **Ghost Record Detection** — Identify when a file matches a soft-deleted record
- **Conflict Resolution UI** — Compare metadata and choose to reactivate or skip ghost records
- **Conflict Reporting** — Stream detailed status for each file during ingestion

---

## Data Integrity & Audit

### Change Tracking
- **Audit Log** — Complete history of all metadata changes with timestamps
- **Batch Operations** — View grouped changes by operation batch
- **Soft Deletes** — Deleted records marked but preserved for audit trail
- **Cascading Operations** — Ensure referential integrity across linked records

### Bulk Cleanup
- **Delete Unlinked Tags** — Remove tags with no associated songs (with safety confirmation)
- **Delete Unlinked Publishers** — Remove publishers with no associated songs or albums (with safety confirmation)
- **Delete Unlinked Identities** — Remove artists with no associated songs, albums, or roles (with safety confirmation)

### Publisher Management
- **Publisher Hierarchies** — Support parent-child publisher relationships (e.g., subsidiary labels)
- **Publisher Search** — Find publishers by name
- **Publisher Detail Views** — See all songs and albums published by a label

### Tag Management
- **Tag Categories** — Organize tags with hierarchical categories (e.g., Genre, Mood, Era)
- **Tag Search** — Find tags by name or category
- **Tag Detail Views** — See all songs tagged with a specific tag
- **Delete Unlinked Tags** — Clean up unused tags

---

## Audio & Playback

### Streaming
- **MP3 Streaming** — Play back ingested tracks directly from the library
- **Range Request Support** — Seek and scrub through audio files

### Visualization
- **Waveform Visualization** — Display 1000 normalized audio peaks for song scrubbing and timeline navigation
- **Lazy Waveform Generation** — Computed on first request, then cached

---

## Technical Stack

- **Backend** — FastAPI-powered REST API (Python)
- **Frontend** — JavaScript/CSS web interface with vanilla JS (no frameworks)
- **Database** — SQLite with custom collation and search optimization
- **Audio** — FFmpeg for format conversion
- **Server** — Runs locally (localhost:8000)
- **Testing** — Python pytest + JavaScript Vitest with jsdom

---

## What's Missing?

Areas to consider for future expansion:

- **Collaborative** — Multi-user support, shared libraries, user accounts
- **Cloud Sync** — Backup and sync metadata to cloud storage
- **Smart Recommendations** — Suggest new music or related artists based on library
- **Playlists** — Create and manage dynamic/static playlists
- **Advanced Search** — Full-text search improvements, saved searches
- **Artwork** — Cover art management, display, and extraction from files
- **Lyrics** — Store and search song lyrics
- **Statistics** — Library analytics, listening history, trends, most-played
- **Mobile** — Native mobile app or responsive mobile UI
- **API Webhooks** — Notifications for library changes
- **Batch Metadata Editor** — Edit multiple songs at once (Multi-Edit)
- **Smart Renaming** — Auto-rename files on disk based on metadata
- **Import Presets** — Save and reuse metadata extraction patterns
- **External Data Sources** — MusicBrainz, AcousticBrainz, Last.fm integration
- **Genre Hierarchies** — Standardized genre taxonomy support
- **Mood/Energy Analysis** — Auto-detect mood/energy from audio

---

## Quick Start

1. **Upload** some MP3/WAV files to populate your library
2. **Review** ingested songs and fill in missing metadata
3. **Organize** into albums and add credits using Spotify integration or manual entry
4. **Manage Artists** — Create identities, link aliases, and build artist trees
5. **Search** for songs by title, artist, tag, or use advanced filters
6. **Play** tracks directly from the app
7. **Maintain** your library with bulk cleanup and duplicate detection tools

