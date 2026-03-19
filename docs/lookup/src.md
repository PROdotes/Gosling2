# Engine Server
*Location: `src/`

---

## engine_server
*Location: `src/engine_server.py`*
**Responsibility**: FastAPI application setup, CORS middleware, and routing for the entire API.

### app: FastAPI
The main FastAPI application instance.

### get_dashboard() -> HTMLResponse
**HTTP**: `GET /`
- Serves the single-page dashboard skeleton from `src/templates/dashboard.html`.
- Loads modular Vanilla JS from `/static/js/dashboard/main.js`.

### /static Mount
**HTTP**: `GET /static/*`
- Serves static assets (CSS, JS) from `src/static/`.
- Must be mounted AFTER all routers to avoid route shadowing.
