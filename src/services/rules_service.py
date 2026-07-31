"""Filing routing rules (json/rules.json).

Ordered, first-match-wins genre-to-path routing rules consumed by
FilingService.evaluate_routing. Mirrors config_service.py's pattern: this
module owns load/validate/persist; FilingService only reads.
"""

import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.engine import config

VALID_TOKENS = {"artist", "title", "year", "genre"}
_TOKEN_RE = re.compile(r"\{(\w+)\}")
_DRIVE_LETTER_RE = re.compile(r"^[A-Za-z]:")


def _check_path_safety(v: str, field_name: str) -> None:
    """Reject a target_path/default_rule that could escape LIBRARY_ROOT.
    FilingService.evaluate_routing only sanitizes illegal filesystem
    characters within each interpolated {token} value -- the literal path
    template itself (this string) passes through untouched, and pathlib's
    `/` operator silently replaces the whole library root if the right-hand
    side turns out to be absolute. Reject that shape here instead."""
    normalized = v.replace("\\", "/")
    if normalized.startswith("/"):
        raise ValueError(
            f"{field_name} must be a relative path (must not start with / or \\)"
        )
    if _DRIVE_LETTER_RE.match(v):
        raise ValueError(
            f"{field_name} must be a relative path (must not include a drive letter)"
        )
    if any(part.strip() == ".." for part in normalized.split("/")):
        raise ValueError(f"{field_name} must not contain '..' path segments")


def _check_tokens(v: str, field_name: str) -> None:
    used = set(_TOKEN_RE.findall(v))
    unknown = used - VALID_TOKENS
    if unknown:
        raise ValueError(
            f"{field_name} uses unknown token(s): {', '.join(sorted(unknown))} "
            f"(valid: {', '.join(sorted(VALID_TOKENS))})"
        )


class RoutingRule(BaseModel):
    match_genres: list[str] = Field(min_length=1)
    target_path: str = Field(min_length=1)

    @field_validator("match_genres")
    @classmethod
    def _genres_non_empty(cls, v: list[str]) -> list[str]:
        if any(not g.strip() for g in v):
            raise ValueError("match_genres entries must not be blank")
        return v

    @field_validator("target_path")
    @classmethod
    def _target_path_tokens(cls, v: str) -> str:
        _check_tokens(v, "target_path")
        _check_path_safety(v, "target_path")
        return v


class RulesFile(BaseModel):
    routing_rules: list[RoutingRule] = Field(default_factory=list)
    default_rule: Optional[str] = None

    @field_validator("default_rule")
    @classmethod
    def _default_rule_tokens(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        _check_tokens(v, "default_rule")
        _check_path_safety(v, "default_rule")
        return v


def load_rules_from(path: Path) -> tuple["RulesFile", list[dict]]:
    """Read rules from ``path``. A missing file is the legitimate default
    state (empty rule list). A file that exists but is not valid for the
    model falls back to an empty rule list and records a warning."""
    if not path.exists():
        return RulesFile(), []
    try:
        text = path.read_text(encoding="utf-8-sig")
        return RulesFile.model_validate_json(text), []
    except Exception as e:  # any parse/validation error -> banner, not a crash
        return RulesFile(), [{"kind": "rules_load", "error": str(e)}]


def get_rules() -> tuple[RulesFile, list[dict]]:
    """Read the current rules.json. FilingService reads its own copy
    independently (constructed fresh per LibraryService), so there is no
    live in-memory instance to keep in sync here."""
    return load_rules_from(config.RENAME_RULES_PATH)


def save_rules(rules: RulesFile) -> RulesFile:
    """Validate and persist the full rule list to json/rules.json."""
    validated = RulesFile.model_validate(rules.model_dump())
    config.RENAME_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.RENAME_RULES_PATH.write_text(
        validated.model_dump_json(indent=2), encoding="utf-8"
    )
    return validated


def resolve_target_for_genre(genre: str) -> dict:
    """Find which rule (if any) a genre would match under the current rules.json,
    mirroring FilingService.evaluate_routing's case-insensitive first-match-wins
    genre lookup. Returns the raw, unresolved target_path template -- no song
    context is available here, so {artist}/{title}/{year}/{genre} tokens stay
    literal. Falls back to default_rule, then to source="none" if neither
    exists (matches evaluate_routing's own failure case)."""
    rules, _ = get_rules()
    genre_lower = genre.strip().lower()

    for index, rule in enumerate(rules.routing_rules):
        if genre_lower in [g.lower() for g in rule.match_genres]:
            return {
                "target_path": rule.target_path,
                "rule_index": index,
                "source": "rule",
            }

    if rules.default_rule:
        return {
            "target_path": rules.default_rule,
            "rule_index": None,
            "source": "default",
        }

    return {"target_path": None, "rule_index": None, "source": "none"}
