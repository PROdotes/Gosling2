---
tags:
  - type/spec
  - status/draft
  - scope/documentation
---

# T-34: Markdown Tagging Conventions

**Status**: Draft (For future formalization)  
**Logged by**: Vesper (2025-12-23)  
**Purpose**: Establish consistent YAML frontmatter vocabulary so agents stop guessing.

---

## 📋 Tag Categories (Observed Patterns)

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

### Status Tags (`status/`)
What's the current state?

| Tag | Meaning |
|-----|---------|
| `status/active` | Currently being worked on |
| `status/planned` | Approved, not started |
| `status/draft` | Work in progress, not final |
| `status/future` | Someday/maybe |
| `status/approved` | Reviewed and approved |
| `status/done` | Completed |
| `status/blocked` | Waiting on dependency |

### Layer Tags (`layer/`)
Which architectural layer?

| Tag | Meaning |
|-----|---------|
| `layer/data` | Database, models, repositories |
| `layer/business` | Services, business logic |
| `layer/presentation` | UI, views, widgets |
| `layer/core` | Core utilities, shared code |

### Domain Tags (`domain/`)
What functional area?

| Tag | Meaning |
|-----|---------|
| `domain/audio` | Audio playback, metadata |
| `domain/database` | DB schema, migrations |
| `domain/import` | File import workflow |
| `domain/tags` | Tagging system |
| `domain/contributors` | Artists, groups, aliases |
| `domain/albums` | Album management |

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
| `size/small` | ~1h work |
| `size/medium` | ~3-5h work |
| `size/large` | ~1 day+ |
| `risk/low` | Safe change |
| `risk/medium` | Some risk |
| `risk/high` | Dangerous, needs review |

---

## 🎯 Recommended Minimum Tags

Every MD should have at least:
1. **One `type/` tag** — What is this?
2. **One `status/` tag** — What state is it in?
3. **Relevant `domain/` tags** — What does it affect?

---

## 📝 Example Frontmatter

```yaml
---
tags:
  - type/proposal
  - status/planned
  - domain/albums
  - layer/data
  - size/medium
  - risk/low
links:
  - "[[DATABASE]]"
  - "[[T-22 Albums]]"
---
```

---

## ⚠️ Notes for Agents

- **Don't invent new tags** without adding them to this document first.
- **Be consistent** — use `domain/audio` not `audio/domain`.
- **When in doubt**, use existing tags from this list.
- **T-34 is Post-0.1** — formalize this fully after legacy parity.
