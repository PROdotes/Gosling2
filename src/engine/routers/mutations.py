from typing import Any

from fastapi import APIRouter, Body

from src.services.logger import logger

router = APIRouter(prefix="/api/v1", tags=["mutations"])


@router.post("/mutate")
async def mutate(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    logger.error(f"[Mutate] received command: {body}")
    return {"status": "received", "echo": body}
