# Engine Server
*Location: `src/engine_server.py`*

**Responsibility**: Entry point, FastAPI app setup, and static UI routes.

---

## UI Engine
*Location: `src/engine_server.py`*
**Responsibility**: Serves the single-page dashboard.

### async def get_dashboard()
**HTTP**: `GET /`
- Serves the `src/templates/dashboard.html` interface.
- Includes embedded Vanilla JS for the search/view logic.
