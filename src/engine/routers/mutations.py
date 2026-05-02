from fastapi import APIRouter, HTTPException

from src.engine.config import get_db_path
from src.engine.routers.mutation_models import MutationRequest
from src.services.logger import logger
from src.services.mutation_coordinator import MutationCoordinator

router = APIRouter(prefix="/api/v1", tags=["mutations"])


def _get_coordinator() -> MutationCoordinator:
    return MutationCoordinator(str(get_db_path()))


@router.post("/mutate")
async def mutate(body: MutationRequest) -> dict:
    logger.debug(f"[Mutate] received: {body.model_dump(exclude_unset=True)}")
    coordinator = _get_coordinator()
    try:
        return coordinator.apply(body)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
