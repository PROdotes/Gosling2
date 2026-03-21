import os
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


def _get_downloads_folder() -> Optional[str]:
    if os.name == "nt":
        return os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")
    elif os.name == "posix":
        home = os.environ.get("HOME", "")
        return os.path.join(home, "Downloads")
    return None


@router.get("/downloads-folder")
async def get_downloads_folder():
    return JSONResponse({"path": _get_downloads_folder()})
