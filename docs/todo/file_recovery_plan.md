# File Recovery Plan — 32 Missing Songs

## Context
32 songs lost during the wipe incident (2026-04-28). DB records intact with full metadata.
Files are in Z:\songs\, ProcessingStatus=0, IsDeleted=1 (zeroed by Recuva, unrecoverable).
Goal: find files, re-link them to existing DB records without disturbing metadata.

## Step 1 — Export the song list
Run on the work machine against the NAS db:
```sql
SELECT ms.SourceID, ms.SourcePath, ms.AudioHash,
       s.Title, s.ArtistName
FROM MediaSources ms
LEFT JOIN Songs s ON s.SourceID = ms.SourceID
WHERE ms.SourcePath LIKE 'Z:/songs/%'
  AND ms.ProcessingStatus = 0
  AND ms.IsDeleted = 1
ORDER BY s.ArtistName, s.Title
```

## Step 2 — Find the files
For each song, try in order:
1. YouTube (yt-dlp)
2. Publisher direct (only if multiple files from same publisher — batch the ask)

yt-dlp command:
```
yt-dlp -x --audio-format mp3 -o "%(artist)s - %(title)s.%(ext)s" "<url>"
```

## Step 3 — Rename to match original filenames
Original filenames are in SourcePath. Rename each downloaded file to match exactly.

## Step 4 — Copy to Z:\songs\
Copy each file to the correct path as it appears in SourcePath.

## Step 5 — Run the migration script
For each recovered file, update the DB:
```sql
-- 1. Recalculate hash (do in Python via calculate_audio_hash)
-- 2. Update the record
UPDATE MediaSources
SET AudioHash = '<new_hash>', IsDeleted = 0
WHERE SourceID = <id>;
```

Or use the existing recover-file endpoint while it's still in the code:
```
POST /api/v1/ingest/recover-file?song_id=<id>&staged_path=<path>
```
This overwrites the file at SourcePath and rehashes automatically.

## Step 6 — Verify
- File exists at SourcePath ✓
- AudioHash updated ✓
- IsDeleted = 0 ✓
- Play button green indicator in app ✓

## Step 7 — Code cleanup (after all files recovered)
Remove the temporary recovery feature added during the incident. It was useful but is not an app feature.

Files to edit:
- `src/services/ingestion_service.py` — remove `recover_file()` method, `shutil` import, and the `ALREADY_EXISTS` staged_path patch in `ingest_file()`
- `src/services/catalog_service.py` — remove `recover_file()` passthrough
- `src/engine/routers/ingest.py` — remove `/recover-file` endpoint
- `src/static/js/dashboard/handlers/song_actions.js` — remove `handleRecoverFile()` and `"recover-file"` from the actions set
- `src/static/js/dashboard/renderers/ingestion.js` — remove the "Recover File" button from `createResultCard`

## Song list
<!-- TODO: paste query results here before starting -->
