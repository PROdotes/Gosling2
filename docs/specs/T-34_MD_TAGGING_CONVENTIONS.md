---
tags:
  - type/spec
  - status/approved
  - scope/documentation
  - domain/metadata
  - target/v0.1
links:
  - "[[TAGS]]"
---

# T-34: Markdown Tagging Conventions

**Status**: Approved
**Logged by**: Vesper (2025-12-23) | **Ratified by**: Antigravity (2025-12-24)
**Purpose**: Establish consistent YAML frontmatter vocabulary so agents stop guessing. This document supersedes `TAGS.md`.

---

## 📋 Tag Categories

### Type Tags (`type/`)
What kind of document is this?

| Tag | Meaning |
|-----|---------|
| `type/proposal` | Design proposal for a feature |
| `type/spec` | Formal specification |
| `type/idea` | Brainstorm / future concept |
| `type/feature` | Feature description |
| `type/index` | Index/registry file |
| `type/strategy` | High-level planning |
| `type/reference` | Reference documentation |
| `type/runbook` | Execution guide (e.g. T-04) |

### Status Tags (`status/`)
What's the current state?

| Tag | Meaning |
|-----|---------|
| `status/active` | Currently being worked on |
| `status/planned` | Approved, ready to start |
| `status/draft` | Work in progress, not final |
| `status/future` | Someday/maybe |
| `status/approved` | Reviewed and approved |
| `status/done` | Completed |
| `status/blocked` | Waiting on dependency |
| `status/deprecated` | Obsolete / Replaced |

### Target Tags (`target/`)
When does this ship? (SemVer)

| Tag | Meaning |
|-----|---------|
| `target/v0.1` | **Legacy Parity**. Must be done for Alpha release. |
| `target/v0.2` | **Refactor/Clean**. Post-parity cleanup & debt payment. |
| `target/v1.0` | **MVP**. The 1.0 General Release feature set. |
| `target/post-1.0` | **Future**. Wishlist items and advanced features. |

### Component Tags (`component/`)
Where in the app does this live? (UI Areas)

| Tag | Meaning |
|-----|---------|
| `component/library` | The Main Table / Grid View. |
| `component/playlist` | The Side/Bottom Playlist Queue. |
| `component/player` | Controls (Play/Pause, Seek, Volume). |
| `component/editor` | Metadata Editor (Panel or Dialog). |
| `component/filter` | Sidebar Filter Tree / Search. |
| `component/settings` | Preferences / Settings Dialog. |
| `component/main` | Main Window shell / Global Layout. |

### Domain Tags (`domain/`)
What functional area?

| Tag | Meaning |
|-----|---------|
| `domain/audio` | **Playback only**. Waveforms, crossfader, volume, audio engine. |
| `domain/metadata` | **Data/Content**. ID3 tags, library strings, database records. |
| `domain/database` | DB schema, migrations (Infrastructure) |
| `domain/import` | File import workflow |
| `domain/contributors` | Artists, groups, aliases |
| `domain/albums` | Album management |
| `domain/audit` | Logging, undo, history |

### Layer Tags (`layer/`)
Which architectural layer?

| Tag | Meaning |
|-----|---------|
| `layer/data` | Database, models, repositories |
| `layer/business` | Services, business logic |
| `layer/presentation` | UI, views, widgets |
| `layer/core` | Core utilities, shared code |

### Scope Tags (`scope/`)
Size/reach of the change?

| Tag | Meaning |
|-----|---------|
| `scope/local` | Single file/component |
| `scope/cross-cutting` | Multiple components |
| `scope/global` | Affects entire app |
| `scope/documentation` | Docs only |
| `scope/post-1.0` | Future version |

### Integration Tags (`integration/`)
External dependencies?

| Tag | Meaning |
|-----|---------|
| `integration/api` | External API call |
| `integration/online` | Requires network |
| `integration/musicbrainz` | MusicBrainz-specific |
| `integration/spotify` | Spotify-specific |

### Size/Risk Tags
| Tag | Meaning |
|-----|---------|
| `size/small` | ~1-4h work |
| `size/medium` | ~1-2 days |
| `size/large` | ~1 week+ |
| `risk/low` | Safe change |
| `risk/medium` | Some risk |
| `risk/high` | Dangerous, needs review |

### Value Tags (`value/`)
Business/User Impact.
| Tag | Meaning |
|-----|---------|
| `value/high` | Major user benefit |
| `value/medium` | Good to have |
| `value/low` | Minor polish |

---

## 🎯 Recommended Minimum Tags

Every MD should have at least:
1. **One `type/` tag** — What is this?
2. **One `status/` tag** — What state is it in?
3. **One `target/` tag** — What release is this for?
4. **Relevant `component/` tags** — Where is it?

---

## 📝 Example Frontmatter

```yaml
---
tags:
  - type/proposal
  - status/planned
  - target/v0.2
  - component/library
  - domain/albums
  - layer/data
  - size/medium
  - risk/low
links:
  - "[[DATABASE]]"
  - "[[T-22 Albums]]"
---
```
