# Engine Server
*Location: `src/`

---

## Models
*Location: `src/models/`*
**Responsibility**: Domain entities and API view models. Not covered by a dedicated lookup doc — read the files directly.

- `domain.py` — core domain dataclasses (Song, SongCredit, MediaSource, etc., 11 classes).
- `view_models.py` — pydantic API views: `SongView`/`SongSlimView`, `AlbumView`/`AlbumSlimView`, `IdentityView`/`IdentitySlimView`, `TagView`, `PublisherView`, `ArtistChipView`, `IngestionReportView`, plus request bodies. Slim views are the list/search shapes; full views hydrate detail endpoints.
- `exceptions.py` — shared exception types (4 classes, e.g. MergeRequiredError).
- `metadata_frames.py` — ID3 frame mapping structures.

Also `src/engine/models/spotify.py` — Spotify parse/import request models.

---

## FilenameParser
*Location: `src/services/filename_parser.py`*
**Responsibility**: Pattern-to-Regex compiler for extracting metadata from filename stems. Supports tokens like {Artist}, {Title}, and {Ignore}.

---


## engine_server
*Location: `src/engine_server.py`*
**Responsibility**: FastAPI application setup, CORS middleware, and routing for the entire API.

### app: FastAPI
The main FastAPI application instance with CORS middleware.

### get_dashboard() -> HTMLResponse
**HTTP**: `GET /`
- Serves the single-page dashboard skeleton from `src/templates/dashboard.html`.
- Loads modular Vanilla JS from `/static/js/dashboard/main.js`.

### add_request_id_middleware(app: FastAPI)
**Internal**: Registers middleware to ensure every request has a unique ID in context vars.

### validation_exception_handler(request: Request, exc: RequestValidationError)
**Internal**: Standardized handler for Pydantic validation errors. Returns 422 with structured details.

### _ensure_db()
**Internal**: Initializes database schema on startup if not exists.

### lifespan
**Internal**: FastAPI lifespan context manager for startup/shutdown events.

### /static Mount
**HTTP**: `GET /static/*`
- Serves static assets (CSS, JS) from `src/static/`.
- Must be mounted AFTER all routers to avoid route shadowing.

---

## Data Schema
*Location: `src/data/schema.py`*
**Responsibility**: Database schema definitions, table creation, and migrations.
