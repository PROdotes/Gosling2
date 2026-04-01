# Upcoming Features (Feature Parity)

## Rule Editor
- UI to view, add, edit, and delete entries in `rules.json` (genre → folder path mappings)
- Should surface the same validation that `evaluate_routing` uses so bad rules fail early
- Probably lives as a settings/admin panel, not in the main song detail flow

## Filename Parser
- Modal: "Parse Metadata from Filename"
- User types a pattern using tokens: `{Artist}`, `{Title}`, `{Album}`, `{Year}`, `{BPM}`, `{Genre}`, `{Publisher}`, `{ISRC}`, `{Ignore}`
- `{Ignore}` skips unwanted segments (track numbers, "Official Video", etc.)
- Presets dropdown with saved patterns, e.g.:
  - `{Artist} - {Title}`
  - `{Artist} - {Album} - {Title}`
  - `{Ignore} - {Artist} - {Title}`
  - `{Title}`
  - `{Artist} - {Title} [{Publisher}]`
  - `{ISRC} - {Artist} - {Title} - {Publisher}`
  - `{Artist} - {Title} - {ISRC}`
  - `{ISRC}_{Title}_{Artist}_{Publisher}`
- Live preview table showing parsed fields per filename as pattern is typed
- Feeds into ingest flow as pre-fill when ID3 tags are sparse/missing
- Save custom presets
- **Two UI modes** (same logic underneath):
  - Power mode: type the pattern string directly (current)
  - Friendly mode: chip builder — click tokens to append them into the pattern slot, reorder by drag, delete with ✕ — same result, no syntax knowledge needed

## Title Case / Sentence Case Button
- Quick action button next to the field, not a modal
- Fields: `media_name`, and credit display names (for ALL CAPS artist names from labels like Crorec)
- Two modes: Title Case (capitalize each word) and Sentence case (capitalize first word only)
- Needs to handle edge cases: articles (a, an, the), conjunctions, prepositions for proper title case

## WAV → MP3 Conversion on Import
- Config setting in `config.py` to enable/disable auto-conversion
- Convert WAV to MP3 during ingest before staging (148 WAVs in current backlog)
- WAV metadata extraction needs to handle both ID3 chunks and RIFF INFO chunks — mutagen supports both but they map differently, test both paths
- Preserve original WAV or discard after conversion — make this a config option

## Bulk / Batch Import UI
- Folder scan + queue UI to ingest multiple files in one flow
- Existing `scan_folder` + `ingest_batch` service methods already exist, need frontend

## Artist Splitter
- Modal: "Split Artists" — for when a credit field contains multiple artists joined by separators
- Tokenizes the raw string — name segments and separator tokens alternate in the display
- Each separator token is independently toggleable: red = active split point, gray = join (keep as part of name)
- This handles edge cases like "Earth, Wind & Fire & ABBA" — turn off the `&` inside the band name, keep the one between artists active
- Add custom split words via text input + "Add Split" button (persisted for the session)
- Split matching must support space-padded tokens (e.g. ` i `) to avoid substring collisions — "oliver dragojevic i prijatelji" should only split on the standalone ` i `, not the `i` inside names. Old version auto-stripped spaces which broke this.
- Preview panel shows resulting entities with "Will Create New" or existing identity match
- On confirm, creates individual credits from the split result

## Bulk Select + Bulk Edit
- Multi-select songs in the list view
- Bulk apply: publisher, tag, album, active toggle
- Low priority for now — albums are rare, manually adding publisher per song is acceptable in the short term
