from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Literal, Optional
from src.services.tokenizer import tokenize_credits, resolve_names
from src.services.filename_parser import parse_with_pattern
from src.services.catalog_service import CatalogService
from src.engine.config import get_db_path

router = APIRouter(prefix="/api/v1/tools", tags=["Tools"])


def _get_service() -> CatalogService:
    return CatalogService(get_db_path())


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
def confirm(
    body: ConfirmRequest, service: CatalogService = Depends(_get_service)
) -> dict:
    """Atomic replacement of one credit/publisher with multiple split results."""
    names = resolve_names(body.tokens)
    if body.target == "credits":
        if not body.classification:
            raise HTTPException(
                status_code=422, detail="classification is required for credits"
            )
        for name in names:
            service.add_song_credit(body.song_id, name, body.classification)
        service.remove_song_credit(body.song_id, body.remove.id)
    elif body.target == "publishers":
        for name in names:
            service.add_song_publisher(body.song_id, publisher_name=name)
        service.remove_song_publisher(body.song_id, body.remove.id)
    return {"ok": True}


class FilenameApplyItem(BaseModel):
    song_id: int
    filename: str


class FilenameApplyRequest(BaseModel):
    items: List[FilenameApplyItem]
    pattern: str


@router.post("/filename-parser/apply")
def filename_parser_apply(
    body: FilenameApplyRequest, service: CatalogService = Depends(_get_service)
) -> dict:
    """
    Parses each filename and applies the resulting metadata to the database.
    - {Artist} -> Adds a 'Performer' credit (if not exists)
    - {Title} -> Updates the song title scalar
    - {Year} -> Updates the recording year scalar
    - {BPM} -> Updates the tempo bpm scalar
    - {ISRC} -> Updates the ISRC scalar
    - {Genre} -> Adds a 'Genre' tag
    - {Publisher} -> Adds a publisher link
    """
    for item in body.items:
        metadata = parse_with_pattern(item.filename, body.pattern)
        if not metadata:
            continue

        # 1. Scalar updates (Title, Year, BPM, ISRC)
        scalars = {}
        if "Title" in metadata:
            scalars["media_name"] = metadata["Title"]
        if "Year" in metadata:
            try:
                scalars["year"] = int(metadata["Year"])
            except ValueError:
                pass
        if "BPM" in metadata:
            try:
                scalars["bpm"] = int(metadata["BPM"])
            except ValueError:
                pass
        if "ISRC" in metadata:
            scalars["isrc"] = metadata["ISRC"]

        if scalars:
            service.update_song_scalars(item.song_id, scalars)

        # 2. Credits (Artist)
        if "Artist" in metadata:
            service.add_song_credit(
                item.song_id, metadata["Artist"], role_name="Performer"
            )

        # 3. Tags (Genre)
        if "Genre" in metadata:
            service.add_song_tag(
                item.song_id, tag_name=metadata["Genre"], category="Genre"
            )

        # 4. Publishers
        if "Publisher" in metadata:
            service.add_song_publisher(
                item.song_id, publisher_name=metadata["Publisher"]
            )

    return {"ok": True, "count": len(body.items)}
