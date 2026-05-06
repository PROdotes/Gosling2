import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Literal, Optional
from src.services.tokenizer import tokenize_credits, resolve_names
from src.services.filename_parser import parse_with_pattern
from src.services.catalog_service import CatalogService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tools", tags=["Tools"])


def _get_service() -> CatalogService:
    return CatalogService()


# --- Filename Parser ---


class FilenamePreviewRequest(BaseModel):
    filenames: List[str]
    pattern: str


@router.post("/filename-parser/preview")
def filename_parser_preview(body: FilenamePreviewRequest) -> dict:
    """
    Returns a preview of metadata extracted from a list of filenames using a pattern.
    Stateless / Utility.
    """
    results = []
    for filename in body.filenames:
        results.append(
            {
                "filename": filename,
                "metadata": parse_with_pattern(filename, body.pattern),
            }
        )
    return {"results": results}


# --- Credit/Publisher Splitter ---


class TokenizeRequest(BaseModel):
    text: str
    separators: List[str]


class PreviewRequest(BaseModel):
    names: List[str]
    target: Literal["credits", "publishers"]


@router.post("/splitter/tokenize")
def tokenize(body: TokenizeRequest) -> List[dict]:
    """Stateless string tokenization for the UI splitter."""
    return tokenize_credits(body.text, body.separators)


@router.post("/splitter/preview")
def preview(
    body: PreviewRequest, service: CatalogService = Depends(_get_service)
) -> List[dict]:
    """Checks whether each split name already exists in the DB."""
    results = []
    for name in body.names:
        res = {"name": name, "exists": False, "identity_id": None}
        if body.target == "credits":
            iid = service.resolve_identity_by_name(name)
            if iid:
                res["exists"] = True
                res["identity_id"] = iid
        else:
            res["exists"] = service.publisher_exists(name)
        results.append(res)
    return results


class RemoveRef(BaseModel):
    type: Literal["credit", "publisher"]
    id: int


class ConfirmRequest(BaseModel):
    song_id: int
    tokens: List[dict]
    target: Literal["credits", "publishers"]
    classification: Optional[str]
    remove: RemoveRef


@router.post("/splitter/confirm")
def confirm(body: ConfirmRequest) -> dict:
    """Returns add/remove payload for splitter confirmation. Does not write."""
    names = resolve_names(body.tokens)
    add = []
    remove = [{"type": body.remove.type, "song_id": body.song_id, "id": body.remove.id}]

    if body.target == "credits":
        if not body.classification:
            raise HTTPException(
                status_code=422, detail="classification is required for credits"
            )
        for name in names:
            add.append(
                {
                    "type": "credit",
                    "song_id": body.song_id,
                    "name": name,
                    "id": None,
                    "role": body.classification,
                }
            )
    elif body.target == "publishers":
        for name in names:
            add.append(
                {"type": "publisher", "song_id": body.song_id, "name": name, "id": None}
            )

    return {"add": add, "remove": remove}


class FilenameApplyItem(BaseModel):
    song_id: int
    filename: str


class FilenameApplyRequest(BaseModel):
    items: List[FilenameApplyItem]
    pattern: str


@router.post("/filename-parser/apply")
def filename_parser_apply(body: FilenameApplyRequest) -> dict:
    """
    Resolves filenames into structured add/update/remove items for the mutator.
    Does not write to the database.
    """
    add = []
    update = []

    for item in body.items:
        metadata = parse_with_pattern(item.filename, body.pattern)
        if not metadata:
            continue

        scalars = {}
        if "Title" in metadata:
            scalars["media_name"] = metadata["Title"]
        if "Year" in metadata:
            try:
                scalars["year"] = int(metadata["Year"])
            except ValueError:
                logger.warning(
                    f"[tools] Non-numeric Year for song {item.song_id}: {metadata['Year']!r}"
                )
        if "BPM" in metadata:
            try:
                scalars["bpm"] = int(metadata["BPM"])
            except ValueError:
                logger.warning(
                    f"[tools] Non-numeric BPM for song {item.song_id}: {metadata['BPM']!r}"
                )
        if "ISRC" in metadata:
            scalars["isrc"] = metadata["ISRC"]

        if scalars:
            update.append({"type": "song", "id": item.song_id, **scalars})

        if "Artist" in metadata:
            add.append(
                {
                    "type": "credit",
                    "song_id": item.song_id,
                    "name": metadata["Artist"],
                    "role": "Performer",
                }
            )

        if "Genre" in metadata:
            add.append(
                {
                    "type": "tag",
                    "song_id": item.song_id,
                    "name": metadata["Genre"],
                    "category": "Genre",
                }
            )

        if "Publisher" in metadata:
            add.append(
                {
                    "type": "publisher",
                    "song_id": item.song_id,
                    "name": metadata["Publisher"],
                }
            )

    result = {}
    if add:
        result["add"] = add
    if update:
        result["update"] = update
    return result


# --- Text Formatting ---

from src.services.casing_service import CasingService


class FormatTextRequest(BaseModel):
    text: str
    type: Literal["title", "sentence"]


@router.post("/format-text")
def format_text(body: FormatTextRequest) -> dict:
    if body.type == "title":
        return {"result": CasingService.to_title_case(body.text)}
    return {"result": CasingService.to_sentence_case(body.text)}
