# Gosling2 Music Library Manager

A professional radio music library application built with PyQt6, featuring strict schema governance, metadata management, and seamless audio playback.

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py
```

---

## ✨ Key Features

- **Drag & Drop Import** — Import MP3s or ZIP archives directly into the library
- **Smart Metadata** — Automatic ID3 tag extraction with discrepancy highlighting
- **Crossfade Playback** — Seamless transitions between tracks
- **Filter & Search** — Browse by Artist, Decade, Genre, or Status
- **Playlist Queue** — Drag and drop songs to build playlists
- **Strict Schema Integrity** — 9-layer validation prevents silent data drift

---

## 🎯 Core Philosophy: Portable Metadata

> **The MP3 file IS the database.**

When you share an MP3 between radio stations, ALL metadata travels with it inside the ID3 tags. The receiving Gosling 2 instance imports the file and auto-populates its database from the embedded tags.

| Field Type | Examples | ID3 Sync |
|------------|----------|----------|
| **Portable** | Artists, Title, Year, ISRC, BPM | ✅ Synced to/from ID3 |
| **Local-only** | Song ID, Play Count, Done Status | ❌ Station-specific |

This design ensures data consistency across stations without external databases or cloud sync.

---

## 🏗️ Architecture

The application follows a clean **3-tier architecture**:

```
┌─────────────────────────────────┐
│   Presentation Layer (UI)       │
│   - Views, Widgets, Dialogs     │
└───────────┬─────────────────────┘
            │
┌───────────▼─────────────────────┐
│   Business Logic Layer          │
│   - LibraryService              │
│   - MetadataService             │
│   - PlaybackService             │
│   - SettingsManager             │
└───────────┬─────────────────────┘
            │
┌───────────▼─────────────────────┐
│   Data Access Layer             │
│   - Models (Song, Contributor)  │
│   - Repositories                │
│   - SQLite Database             │
└─────────────────────────────────┘
```

### Project Structure

```
Gosling2/
├── src/
│   ├── data/              # Data Access Layer
│   │   ├── models/        # Song, Contributor, Role dataclasses
│   │   └── repositories/  # Database operations
│   ├── business/          # Business Logic Layer
│   │   └── services/      # Library, Metadata, Playback services
│   └── presentation/      # Presentation Layer
│       ├── views/         # MainWindow
│       └── widgets/       # Library, Playlist, Filter widgets
├── tests/
│   ├── unit/              # 250+ unit tests
│   └── integration/       # Integration tests
├── app.py                 # Entry point
├── requirements.txt       # Production dependencies
├── DATABASE.md            # Schema specification
└── TESTING.md             # Test strategy
```

---

## 🧪 Testing

**260+ tests**, all passing:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/unit/data/test_database_schema.py
```

| Category | Tests | Status |
|----------|-------|--------|
| Data Models | ~20 | ✅ |
| Repositories | ~30 | ✅ |
| Services | ~120 | ✅ |
| Schema Strictness | ~50 | ✅ |
| Integration | ~40 | ✅ |

---

## 📦 Dependencies

### Production
- `PyQt6 >= 6.4.0` — UI framework
- `mutagen >= 1.45.1` — Audio metadata

### Development
- `pytest >= 7.4.0` — Testing
- `pytest-cov >= 4.1.0` — Coverage
- `pytest-qt >= 4.2.0` — Qt testing

---

## 🎓 Design Patterns

- **Repository Pattern** — Data access abstraction
- **Service Layer Pattern** — Business logic encapsulation
- **Model-View Pattern** — UI separation
- **Dependency Injection** — Loose coupling between layers
- **Context Managers** — Safe resource handling

---

## 🐛 Troubleshooting

### Import Errors
```bash
pip install -r requirements.txt
```

### Database Not Found
The database is created automatically at `sqldb/gosling2.sqlite3` on first run.

### Tests Failing
```bash
pip install -r requirements-dev.txt
pytest -v
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| [DATABASE.md](DATABASE.md) | Schema specification & governance |
| [TESTING.md](TESTING.md) | Test strategy & "9 layers of yell" |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Detailed architecture guide |
| [tasks.md](tasks.md) | Development roadmap |

---

## 🔮 Roadmap

See [tasks.md](tasks.md) for the current development roadmap, including:
- Type Tabs (filter by content type)
- Field Registry (centralized field definitions)
- Transaction Logging (undo/audit)
- Broadcast Automation (future)

---

## 📄 License

MIT License
