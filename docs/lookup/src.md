# Engine Server
*Location: `src/`

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
