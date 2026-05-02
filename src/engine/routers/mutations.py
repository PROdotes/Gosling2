from fastapi import APIRouter

from src.engine.routers.mutation_models import MutationRequest
from src.services.logger import logger

router = APIRouter(prefix="/api/v1", tags=["mutations"])


@router.post("/mutate")
async def mutate(body: MutationRequest) -> dict:
    logger.debug(f"[Mutate] received command: {body}")
    return {"status": "received", "echo": body.model_dump(exclude_unset=True)}
