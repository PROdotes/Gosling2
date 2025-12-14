# Migration Guide: Old to New Architecture

## Overview
This document explains how to migrate from the old single-file application to the new 3-tier architecture.

## Key Changes

### File Organization

**Old Structure:**
```
Gosling2/
├── main.py          # Everything in one file (~1000 lines)
├── Song.py          # Song class
├── db_manager.py    # Database operations
└── sqldb/           # Database directory
```

**New Structure:**
```
Gosling2/
├── app.py                          # Entry point
├── src/
│   ├── data/                       # Data layer
│   │   ├── models/                 # Data models
│   │   └── repositories/           # Database operations
│   ├── business/                   # Business logic layer
│   │   └── services/               # Business services
│   └── presentation/               # UI layer
│       ├── views/                  # Windows
│       └── widgets/                # Custom widgets
├── tests/                          # Test suite
└── sqldb/                          # Database directory
```

## Migration Steps

### Step 1: Backup Your Data

Before migrating, backup your database:

```bash
# Backup your database
copy sqldb\gosling2.sqlite3 sqldb\gosling2.sqlite3.backup
```

### Step 2: Install Dependencies

The new application has the same core dependencies but organized differently:

```bash
# Install new dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

### Step 3: Database Compatibility

**Good news!** The database schema is compatible. The new application will work with your existing database.

Location: `sqldb/gosling2.sqlite3` (same as before)

### Step 4: Running the New Application

**Old way:**
```bash
python main.py
```

**New way:**
```bash
python app.py
```

### Step 5: Settings Migration

Settings are stored in the same location using QSettings:
- Organization: "Prodo"
- Application: "Gosling2"

**Note:** The new `SettingsManager` uses namespaced keys (e.g., `window/geometry` instead of `geometry`). Consequently, previous window positions and volume settings will **reset to defaults** upon the first run of the new application.

## Code Mapping

### Song Class

**Old:** `Song.py`
```python
class Song:
    def __init__(self, file_id=None, path=None, ...):
        self.file_id = file_id
        # ...
```

**New:** `src/data/models/song.py`
```python
@dataclass
class Song:
    file_id: Optional[int] = None
    # ... with type hints and helper methods
```

### Database Operations

**Old:** `db_manager.py` - `DBManager` class
```python
db_manager = DBManager()
db_manager.insert_file_basic(path)
db_manager.fetch_all_library_data()
```

**New:** `src/data/repositories/` - Repository pattern
```python
song_repo = SongRepository()
song_repo.insert(path)
song_repo.get_all()
```

### Business Logic

**Old:** Mixed in `main.py`

**New:** Separated into services in `src/business/services/`
```python
# Library operations
library_service = LibraryService()
library_service.add_file(path)

# Metadata extraction
metadata_service = MetadataService()
song = metadata_service.extract_from_mp3(path)

# Playback control
playback_service = PlaybackService()
playback_service.play()

# Settings management
settings_manager = SettingsManager()
volume = settings_manager.get_volume()
```

### UI Components

**Old:** Everything in `MainWindow` class in `main.py`

**New:** Separated into views and widgets
- Main window: `src/presentation/views/main_window.py`
- Library view: `src/presentation/widgets/library_widget.py`
- Playback controls: `src/presentation/widgets/playback_control_widget.py`
- Playlist widget: `src/presentation/widgets/playlist_widget.py`
- Search filter: `src/presentation/widgets/filter_widget.py`

## Feature Parity

All features from the old application are preserved:

| Feature | Old | New | Notes |
|---------|-----|-----|-------|
| Import files | ✓ | ✓ | Same functionality |
| Scan folder | ✓ | ✓ | Same functionality |
| Library view | ✓ | ✓ | Same layout |
| Search | ✓ | ✓ | Same functionality |
| Playlist | ✓ | ✓ | Enhanced drag-drop |
| Playback | ✓ | ✓ | Same controls |
| Metadata | ✓ | ✓ | Same extraction |
| Database | ✓ | ✓ | Compatible schema |

## New Features

The new architecture enables:

1. **Unit Tests**: Comprehensive test coverage
2. **Better Maintainability**: Clear separation of concerns
3. **Easier Extensions**: Add features without touching other layers
4. **Better Error Handling**: Isolated error handling per layer
5. **Type Safety**: Full type hints throughout

## Troubleshooting

### Database Not Found

If you see database errors:
```bash
# Check database location
dir sqldb
```

The database should be at `sqldb/gosling2.sqlite3`

### Import Errors

If you see import errors:
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Settings Not Migrated

Settings are stored in:
- Windows: Registry under `HKEY_CURRENT_USER\Software\Prodo\Gosling2`
- Linux: `~/.config/Prodo/Gosling2.conf`
- macOS: `~/Library/Preferences/com.Prodo.Gosling2.plist`

They should migrate automatically.

## Reverting to Old Version

If you need to revert:

1. Your database is compatible with both versions
2. Simply run the old `main.py` file
3. All data will be intact

## Testing the New Application

Run the test suite to verify everything works:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/unit/test_song_model.py
```

## Getting Help

- Check `README.md` for usage instructions
- Check `ARCHITECTURE.md` for architecture details
- Review test files in `tests/` for usage examples

## Benefits of the New Architecture

1. **Testability**: Each component can be tested independently
2. **Maintainability**: Changes are isolated to specific layers
3. **Scalability**: Easy to add new features
4. **Clarity**: Clear responsibility for each component
5. **Reusability**: Services can be reused across different UIs
6. **Type Safety**: Comprehensive type hints
7. **Best Practices**: Follows industry-standard patterns

## Next Steps

After migration:

1. Test all functionality with your existing data
2. Explore the test suite in `tests/`
3. Read the architecture documentation
4. Start using the new development workflow
5. Contribute improvements!

## Questions?

For questions or issues:
1. Check the test files for examples
2. Review the architecture documentation
3. Examine the code comments and docstrings

