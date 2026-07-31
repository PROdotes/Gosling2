from fastapi import APIRouter, HTTPException

from src.services.rules_service import (
    RulesFile,
    get_rules,
    resolve_target_for_genre,
    save_rules,
)

router = APIRouter(prefix="/api/v1", tags=["rules"])


@router.get("/rules")
def get_filing_rules() -> dict:
    """Current filing routing rules read fresh from json/rules.json, plus any
    load warnings. FilingService reloads its own copy per LibraryService
    construction, so reading here never disturbs anything running."""
    fresh, warnings = get_rules()
    return {"rules": fresh.model_dump(mode="json"), "warnings": warnings}


@router.get("/rules/resolve")
def resolve_filing_rule(genre: str) -> dict:
    """Which rule (if any) the given genre would match, for display next to a
    Genre tag -- e.g. in the Edit Tag modal. Returns the raw target_path
    template with tokens unresolved (no song context is available for a bare
    genre lookup)."""
    return resolve_target_for_genre(genre)


@router.post("/rules")
def update_filing_rules(body: dict) -> dict:
    """Validate and persist the full ordered rule list to json/rules.json.
    A rule using an unknown {token} or an empty match_genres list returns 400
    and writes nothing."""
    try:
        rules = RulesFile.model_validate(body)
        updated = save_rules(rules)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"rules": updated.model_dump(mode="json"), "warnings": []}
