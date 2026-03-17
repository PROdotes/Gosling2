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
- Serves the single-page dashboard from `src/templates/dashboard.html`.
- Includes embedded Vanilla JS for search/view logic.
