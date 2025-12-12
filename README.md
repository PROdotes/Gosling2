# Gosling2 Music Library and Player

A desktop music library and player application built with PyQt6 using 3-tier architecture.

## Features

- Music library management with metadata extraction
- Audio playback with playlist support
- Search and filter functionality
- Drag and drop support
- Custom UI components

## Architecture

The application follows a 3-tier architecture:

### 1. Data Access Layer (`src/data/`)
- **Models**: Data entities (Song, Contributor, Role)
- **Repositories**: Database operations (SongRepository, ContributorRepository)
- **Database**: SQLite database with proper schema management

### 2. Business Logic Layer (`src/business/`)
- **LibraryService**: Music library management
- **MetadataService**: Audio file metadata extraction
- **PlaybackService**: Audio playback control
- **SettingsManager**: Application settings persistence

### 3. Presentation Layer (`src/presentation/`)
- **Views**: Main application window
- **Widgets**: Custom UI components (LibraryWidget, FilterWidget, PlaylistWidget, etc.)
- **Dialogs**: User interaction dialogs

## Project Structure

```
Gosling2/
├── src/
│   ├── data/
│   │   ├── models/
│   │   │   ├── song.py
│   │   │   ├── contributor.py
│   │   │   └── role.py
│   │   ├── repositories/
│   │   │   ├── base_repository.py
│   │   │   ├── song_repository.py
│   │   │   └── contributor_repository.py
│   │   └── database_config.py
│   ├── business/
│   │   └── services/
│   │       ├── library_service.py
│   │       ├── metadata_service.py
│   │       ├── playback_service.py
│   │       └── settings_manager.py
│   └── presentation/
│       ├── views/
│       │   └── main_window.py
│       └── widgets/
│           ├── library_widget.py
│           ├── filter_widget.py
│           ├── playlist_widget.py
│           ├── playback_control_widget.py
│           └── seek_slider.py
├── tests/
│   ├── unit/
│   └── integration/
├── app.py
├── requirements.txt
├── README.md
└── DATABASE.md
```

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python app.py
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/unit/test_song_model.py
```

## Development

### Design Patterns Used
- **Repository Pattern**: For data access abstraction
- **Service Layer Pattern**: For business logic encapsulation
- **Model-View Pattern**: For UI separation
- **Dependency Injection**: For loose coupling between layers

### Best Practices
- Clear separation of concerns
- Single Responsibility Principle
- Context managers for resource management
- Type hints for better code documentation
- Comprehensive unit tests

## License

MIT License

