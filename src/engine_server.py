import os
import anyio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from src.engine.routers.catalog import router as catalog_router
from src.engine.routers.metabolic import router as metabolic_router
from src.engine.routers.audit import router as audit_router
from src.engine.routers.ingest import router as ingest_router
from src.services.logger import logger

from src.engine.config import TRUSTED_ORIGINS

app = FastAPI(title="GOSLING2 Engine")

# CORS middleware (restricted to trusted origins - Audit #4)
app.add_middleware(
    CORSMiddleware,
    allow_origins=TRUSTED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the single-page dashboard."""
    logger.info("[EngineServer] Serving Dashboard UI")
    template_path = os.path.join(
        os.path.dirname(__file__), "templates", "dashboard.html"
    )

    if not os.path.exists(template_path):
        logger.error(f"[EngineServer] Dashboard template missing at: {template_path}")
        raise HTTPException(status_code=404, detail="Dashboard UI template not found")

    def _read_file():
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    html = await anyio.to_thread.run_sync(_read_file)
    logger.debug(f"[EngineServer] Loaded dashboard template ({len(html)} bytes)")
    return html


app.include_router(catalog_router)
app.include_router(metabolic_router)
app.include_router(audit_router)
app.include_router(ingest_router)
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)
