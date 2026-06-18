from fastapi import APIRouter, HTTPException

from src.engine import config
from src.services.config_service import Settings, load_settings_from, save_settings

router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get("/settings")
def get_settings() -> dict:
    """Current settings values read fresh from json/settings.json, the JSON
    schema the editor form is generated from, and any load warnings. Reads the
    file for display without disturbing the live settings instance, so a
    corrupt file surfaces as a banner without affecting running read sites."""
    fresh, warnings = load_settings_from(config.SETTINGS_PATH)
    return {
        "settings": fresh.model_dump(mode="json"),
        "schema": Settings.model_json_schema(),
        "warnings": warnings,
    }


@router.post("/settings")
def update_settings(patch: dict) -> dict:
    """Validate a partial settings dict, persist the full settings to
    json/settings.json, and push the values onto the live settings instance so
    they take effect without a restart. Unknown keys or values that fail field
    validation return 400 and write nothing."""
    try:
        updated = save_settings(patch)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"settings": updated.model_dump(mode="json"), "warnings": []}
