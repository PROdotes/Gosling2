"""
Project Structure Documentation

Gosling2 - Music Library and Player Application
================================================

This document describes the architecture and structure of the Gosling2 application.

## Architecture Overview

The application follows a 3-tier architecture pattern:

```
┌─────────────────────────────────────────────┐
│       Presentation Layer (UI)               │
│  - Views: Main window and dialogs           │
│  - Widgets: Custom UI components            │
│  - Handles user interaction                 │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│       Business Logic Layer                  │
│  - Services: Business operations            │
│  - Domain logic and validation              │
│  - Orchestrates data flow                   │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│       Data Access Layer                     │
│  - Models: Data entities                    │
│  - Repositories: Database operations        │
│  - Database connection management           │
└─────────────────────────────────────────────┘
```

## Directory Structure

```
Gosling2/
├── src/                          # Source code
│   ├── data/                     # Data Access Layer
│   │   ├── models/               # Data models
│   │   │   ├── __init__.py
│   │   │   ├── song.py           # Song entity
│   │   │   ├── contributor.py    # Contributor entity
│   │   │   └── role.py           # Role entity
│   │   ├── repositories/         # Data repositories
│   │   │   ├── __init__.py
│   │   │   ├── base_repository.py      # Base repository with DB operations
│   │   │   ├── song_repository.py      # Song data access
│   │   │   └── contributor_repository.py # Contributor data access
│   │   ├── __init__.py
│   │   └── database_config.py    # Database configuration
│   │
│   ├── business/                 # Business Logic Layer
│   │   ├── services/             # Business services
│   │   │   ├── __init__.py
│   │   │   ├── library_service.py      # Library management
│   │   │   ├── metadata_service.py     # Metadata extraction
│   │   │   └── playback_service.py     # Playback control
│   │   └── __init__.py
│   │
│   ├── presentation/             # Presentation Layer
│   │   ├── views/                # Main views
│   │   │   ├── __init__.py
│   │   │   └── main_window.py    # Main application window
│   │   ├── widgets/              # Custom widgets
│   │   │   ├── __init__.py
│   │   │   ├── seek_slider.py    # Custom seek slider
│   │   │   └── playlist_widget.py # Custom playlist widget
│   │   ├── dialogs/              # Dialog windows
│   │   │   └── __init__.py
│   │   └── __init__.py
│   │
│   ├── resources/                # Application resources
│   │   └── constants.py          # Constants and configuration
│   │
│   └── __init__.py
│
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   │   ├── __init__.py
│   │   ├── test_song_model.py
│   │   ├── test_contributor_model.py
│   │   ├── test_role_model.py
│   │   ├── test_song_repository.py
│   │   ├── test_library_service.py
│   │   └── test_playback_service.py
│   ├── integration/              # Integration tests
│   │   ├── __init__.py
│   │   └── test_main_window_integration.py
│   ├── __init__.py
│   └── conftest.py               # Test configuration
│
├── sqldb/                        # Database directory (auto-created)
│   └── gosling2.sqlite3          # SQLite database
│
├── app.py                        # Application entry point
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── pyproject.toml                # Project configuration
├── pytest.ini                    # Pytest configuration
├── .gitignore                    # Git ignore file
└── README.md                     # Project documentation
```

## Layer Responsibilities

### 1. Data Access Layer (src/data/)

**Purpose**: Manages all database operations and data persistence.

**Components**:
- **Models**: Plain data classes using dataclasses
  - `Song`: Represents a music track with metadata
  - `Contributor`: Represents artists, composers, etc.
  - `Role`: Represents contributor roles (Performer, Composer, etc.)

- **Repositories**: Handle database CRUD operations
  - `BaseRepository`: Provides database connection management
  - `SongRepository`: Song-specific database operations
  - `ContributorRepository`: Contributor-specific operations

**Key Features**:
- Context managers for safe database connections
- Automatic schema creation and migration
- Foreign key enforcement
- Transaction management

### 2. Business Logic Layer (src/business/)

**Purpose**: Contains business rules and orchestrates operations.

**Services**:
- **LibraryService**: 
  - Add/remove songs from library
  - Update song metadata
  - Query library data
  - Manage contributors

- **MetadataService**:
  - Extract metadata from MP3 files
  - Parse ID3 tags
  - Handle various tag formats
  - Normalize metadata

- **PlaybackService**:
  - Control audio playback
  - Manage playlist
  - Volume control
  - Playback state management

**Key Features**:
- Separation of business logic from UI
- Reusable service methods
- Independent of presentation layer

### 3. Presentation Layer (src/presentation/)

**Purpose**: Handles user interface and user interaction.

**Views**:
- **MainWindow**: Main application window
  - Library browser
  - Playlist management
  - Playback controls
  - Search functionality

**Widgets**:
- **SeekSlider**: Custom slider with time tooltip
- **PlaylistWidget**: Drag-and-drop playlist with custom rendering

**Key Features**:
- PyQt6-based UI
- Custom styled components
- Responsive layout
- Drag and drop support

## Design Patterns

### Repository Pattern
- Abstracts data access logic
- Provides a collection-like interface
- Encapsulates database operations

### Service Layer Pattern
- Encapsulates business logic
- Provides transactional boundary
- Coordinates between repositories

### Dependency Injection
- Services inject repositories
- Views inject services
- Loose coupling between layers

### Model-View Pattern
- Separation of data and presentation
- Qt's model/view architecture
- Proxy models for filtering/sorting

## Database Schema

```sql
Tables:
- Files: Stores file information
- Contributors: Stores artist/composer information
- Roles: Defines contributor roles
- FileContributorRoles: Links files, contributors, and roles
- GroupMembers: Defines group memberships
```

## Testing Strategy

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Fast execution
- High coverage of business logic

### Integration Tests
- Test interaction between components
- Use temporary databases
- Test UI components with pytest-qt
- Verify end-to-end workflows

## Best Practices Implemented

1. **Separation of Concerns**: Each layer has specific responsibilities
2. **Single Responsibility Principle**: Each class has one reason to change
3. **Dependency Inversion**: Depend on abstractions, not concretions
4. **Type Hints**: Comprehensive type annotations
5. **Context Managers**: Safe resource management
6. **Dataclasses**: Clean data models
7. **Comprehensive Tests**: Unit and integration tests
8. **Documentation**: Code comments and docstrings
9. **Configuration**: External configuration files
10. **Error Handling**: Graceful error handling

## Running the Application

### Development Mode
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest

# Run application
python app.py
```

### Production Mode
```bash
# Install only production dependencies
pip install -r requirements.txt

# Run application
python app.py
```

## Future Enhancements

1. **Additional Features**:
   - Playlist persistence
   - Equalizer
   - Visualizations
   - Tag editing
   - Album art display

2. **Architecture Improvements**:
   - Caching layer
   - Event bus for loose coupling
   - Plugin system
   - Configuration management

3. **Testing**:
   - End-to-end tests
   - Performance tests
   - UI automation tests

## Contributing

When contributing, maintain the 3-tier architecture:
1. Add new data models in `src/data/models/`
2. Add repository methods in `src/data/repositories/`
3. Add business logic in `src/business/services/`
4. Add UI components in `src/presentation/`
5. Add tests for all new code

## License

MIT License
"""

