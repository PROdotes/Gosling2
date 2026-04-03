from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.models.view_models import (
    SongView,
    SongSlimView,
    AlbumSlimView,
    AlbumView,
    TagView,
    PublisherView,
    IdentityView,
    IngestionCheckRequest,
    IngestionReportView,
)
from src.services.catalog_service import CatalogService
from src.services.logger import logger
from src.engine.config import (
    get_db_path,
    SCALAR_VALIDATION,
    TAG_DEFAULT_CATEGORY,
    TAG_CATEGORY_DELIMITER,
    TAG_INPUT_FORMAT,
    DEFAULT_SEARCH_ENGINE,
    DEFAULT_CREDIT_SEPARATORS,
)
from fastapi import Depends
from src.services.search_service import SearchService

router = APIRouter(prefix="/api/v1", tags=["catalog"])


def _get_service() -> CatalogService:
    """Centralized service factory for the router."""
    return CatalogService(get_db_path())


@router.get("/songs/search", response_model=List[SongSlimView])
async def search_songs(
    q: Optional[str] = None, query: Optional[str] = None, deep: bool = False
) -> List[SongSlimView]:
    """Search for songs. Returns slim list-view models. Use 'deep=true' for full resolution."""
    search_term = q or query or ""
    logger.debug(f"[CatalogRouter] search_songs(q='{search_term}', deep={deep})")

    service = _get_service()
    if deep and search_term:
        rows = service.search_songs_deep_slim(search_term)
    else:
        rows = service.search_songs_slim(search_term)

    logger.debug(f"[CatalogRouter] search_songs results={len(rows)}")
    return [SongSlimView.from_row(r) for r in rows]


@router.get("/songs/{song_id:int}", response_model=SongView)
async def get_song(song_id: int) -> SongView:
    """Fetch a single song by ID and hydrate with UI-specific previews."""
    logger.debug(f"[CatalogRouter] get_song(id={song_id})")
    service = _get_service()
    song = service.get_song(song_id)
    if not song:
        logger.warning(f"[CatalogRouter] Song ID {song_id} not found")
        raise HTTPException(status_code=404, detail=f"Song ID {song_id} not found")

    view = SongView.from_domain(song)

    # Calculate previews if in staging
    source_path = (song.source_path or "").lower()
    if "staging" in source_path:
        from pathlib import Path

        # 1. Estimated original source path (Downloads heuristic - metadata independent)
        try:
            from src.engine.config import get_downloads_folder
            downloads = get_downloads_folder()
            if downloads:
                # Extract original filename from UUID prefix (36 hex + 1 underscore)
                filename = Path(song.source_path).name
                if len(filename) > 37 and "_" in filename[:38]:
                    original_name = filename.split("_", 1)[1]
                    view.estimated_original_path = str(Path(downloads) / original_name)
                else:
                    # Fallback for non-UUID files already in staging
                    view.estimated_original_path = str(Path(downloads) / filename)

                # Check if it actually exists (to color code the UI)
                import os
                if os.path.exists(view.estimated_original_path):
                    view.original_exists = True

        except Exception as e:
            logger.debug(f"[CatalogRouter] Original path preview failed for song {song_id}: {e}")

        # 2. Organized destination preview (May fail due to metadata error)
        try:
            from src.engine.config import get_library_root

            root = Path(get_library_root())
            preview = service._filing_service.evaluate_routing(song)
            view.organized_path_preview = str(root / preview)
        except Exception as e:
            logger.debug(
                f"[CatalogRouter] Routing preview skipped for song {song_id}: {e}"
            )
            view.organized_path_preview = f"[Routing error] {e}"

    return view


@router.get("/identities/{identity_id:int}", response_model=IdentityView)
async def get_identity(identity_id: int) -> IdentityView:
    """Fetch a full identity tree by ID."""
    logger.debug(f"[CatalogRouter] get_identity(id={identity_id})")
    identity = _get_service().get_identity(identity_id)
    if not identity:
        logger.warning(
            f"[CatalogRouter] VIOLATION: Identity ID {identity_id} not found"
        )
        raise HTTPException(
            status_code=404, detail=f"Identity ID {identity_id} not found"
        )
    return IdentityView.from_domain(identity)


@router.get("/identities", response_model=List[IdentityView])
async def get_all_identities() -> List[IdentityView]:
    """Fetch a list of active artists/identities."""
    logger.debug("[CatalogRouter] get_all_identities()")
    identities = _get_service().get_all_identities()
    return [IdentityView.from_domain(i) for i in identities]


@router.get("/identities/search", response_model=List[IdentityView])
async def search_identities(q: str) -> List[IdentityView]:
    """Search for identities by name or alias."""
    logger.debug(f"[CatalogRouter] search_identities(q='{q}')")
    identities = _get_service().search_identities(q)
    return [IdentityView.from_domain(i) for i in identities]


class AddAliasBody(BaseModel):
    display_name: str
    name_id: Optional[int] = None


@router.post("/identities/{identity_id:int}/aliases")
async def add_identity_alias(identity_id: int, body: AddAliasBody) -> dict:
    """Add or re-link an alias name to an identity."""
    try:
        # Pass the name_id from the body to the service for Truth-First re-linking
        name_id = _get_service().add_identity_alias(
            identity_id, body.display_name, name_id=body.name_id
        )
        return {"name_id": name_id, "display_name": body.display_name}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/identities/{identity_id:int}/aliases/{name_id:int}", status_code=204)
async def remove_identity_alias(identity_id: int, name_id: int) -> None:  # noqa: ARG001
    """Remove an alias from an identity."""
    try:
        _get_service().remove_identity_alias(name_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class UpdateLegalNameBody(BaseModel):
    legal_name: Optional[str] = None


@router.patch("/identities/{identity_id:int}/legal-name", status_code=204)
async def update_identity_legal_name(identity_id: int, body: UpdateLegalNameBody) -> None:
    """Update the legal name of an identity."""
    try:
        _get_service().update_identity_legal_name(identity_id, body.legal_name)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/identities/{identity_id:int}/songs", response_model=List[SongView])
async def get_songs_by_identity(identity_id: int) -> List[SongView]:
    """Fetch all complete songs associated with a full universal identity tree."""
    logger.debug(f"[CatalogRouter] get_songs_by_identity(id={identity_id})")

    # We first ensure the identity exists
    identity = _get_service().get_identity(identity_id)
    if not identity:
        logger.warning(
            f"[CatalogRouter] VIOLATION: Identity ID {identity_id} not found"
        )
        raise HTTPException(
            status_code=404, detail=f"Identity ID {identity_id} not found"
        )

    songs = _get_service().get_songs_by_identity(identity_id)
    return [SongView.from_domain(s) for s in songs]


@router.get("/publishers", response_model=List[PublisherView])
async def get_all_publishers() -> List[PublisherView]:
    """Fetch a list of all active music publishers."""
    logger.debug("[CatalogRouter] get_all_publishers()")
    return [
        PublisherView.model_validate(p.model_dump())
        for p in _get_service().get_all_publishers()
    ]


@router.get("/publishers/search", response_model=List[PublisherView])
async def search_publishers(q: str) -> List[PublisherView]:
    """Search for publishers by name."""
    logger.debug(f"[CatalogRouter] search_publishers(q='{q}')")
    return [
        PublisherView.model_validate(p.model_dump())
        for p in _get_service().search_publishers(q)
    ]


@router.get("/publishers/{publisher_id:int}", response_model=PublisherView)
async def get_publisher(publisher_id: int) -> PublisherView:
    """Fetch a single publisher by ID."""
    logger.debug(f"[CatalogRouter] get_publisher(id={publisher_id})")
    publisher = _get_service().get_publisher(publisher_id)
    if not publisher:
        logger.warning(f"[CatalogRouter] Publisher ID {publisher_id} not found")
        raise HTTPException(
            status_code=404, detail=f"Publisher ID {publisher_id} not found"
        )
    return PublisherView.model_validate(publisher.model_dump())


@router.get("/publishers/{publisher_id:int}/songs", response_model=List[SongView])
async def get_songs_by_publisher(publisher_id: int) -> List[SongView]:
    """Fetch the full repertoire associated with a given publisher."""
    logger.debug(f"[CatalogRouter] get_songs_by_publisher(id={publisher_id})")
    # Verify existence
    pub = _get_service().get_publisher(publisher_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publisher not found")

    songs = _get_service().get_songs_by_publisher(publisher_id)
    return [SongView.from_domain(s) for s in songs]


@router.get("/albums", response_model=List[AlbumSlimView])
async def get_all_albums() -> List[AlbumSlimView]:
    """Fetch a list of all albums."""
    logger.debug("[CatalogRouter] get_all_albums()")
    rows = _get_service().search_albums_slim("")
    return [AlbumSlimView.from_row(r) for r in rows]


@router.get("/albums/search", response_model=List[AlbumSlimView])
async def search_albums(q: str) -> List[AlbumSlimView]:
    """Search albums by title."""
    logger.debug(f"[CatalogRouter] search_albums(q='{q}')")
    rows = _get_service().search_albums_slim(q)
    return [AlbumSlimView.from_row(r) for r in rows]


@router.get("/albums/{album_id:int}", response_model=AlbumView)
async def get_album(album_id: int) -> AlbumView:
    """Fetch a single album by ID."""
    logger.debug(f"[CatalogRouter] get_album(id={album_id})")
    album = _get_service().get_album(album_id)
    if not album:
        logger.warning(f"[CatalogRouter] Album ID {album_id} not found")
        raise HTTPException(status_code=404, detail=f"Album ID {album_id} not found")

    # Satisfaction for Pyright: proven non-None by raising above
    return AlbumView.from_domain(album)


@router.get("/tags", response_model=List[TagView])
async def get_all_tags() -> List[TagView]:
    """Fetch a list of all tags."""
    logger.debug("[CatalogRouter] get_all_tags()")
    return [
        TagView.model_validate(t.model_dump()) for t in _get_service().get_all_tags()
    ]


@router.get("/tags/categories", response_model=List[str])
async def get_tag_categories() -> List[str]:
    """Fetch all distinct tag categories."""
    logger.debug("[CatalogRouter] get_tag_categories()")
    return _get_service().get_tag_categories()


@router.get("/tags/search", response_model=List[TagView])
async def search_tags(q: str) -> List[TagView]:
    """Search for tags by name."""
    logger.debug(f"[CatalogRouter] search_tags(q='{q}')")
    return [
        TagView.model_validate(t.model_dump()) for t in _get_service().search_tags(q)
    ]


@router.get("/tags/{tag_id:int}", response_model=TagView)
async def get_tag(tag_id: int) -> TagView:
    """Fetch a single tag by ID."""
    logger.debug(f"[CatalogRouter] get_tag(id={tag_id})")
    tag = _get_service().get_tag(tag_id)
    if not tag:
        logger.warning(f"[CatalogRouter] Tag ID {tag_id} not found")
        raise HTTPException(status_code=404, detail=f"Tag ID {tag_id} not found")
    return TagView.model_validate(tag.model_dump())


@router.get("/tags/{tag_id:int}/songs", response_model=List[SongView])
async def get_songs_by_tag(tag_id: int) -> List[SongView]:
    """Fetch all complete songs linked to this tag."""
    logger.debug(f"[CatalogRouter] get_songs_by_tag(id={tag_id})")
    # Verify existence
    tag = _get_service().get_tag(tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    songs = _get_service().get_songs_by_tag(tag_id)
    return [SongView.from_domain(s) for s in songs]


@router.get("/songs/{song_id:int}/web-search")
async def get_song_web_search(
    song_id: int,
    engine: Optional[str] = None,
    service: CatalogService = Depends(_get_service),
):
    """Generates an external search URL for a song."""
    logger.debug(f"[CatalogRouter] get_song_web_search(id={song_id}, engine={engine})")
    song = service.get_song(song_id)
    if not song:
        logger.warning(f"[CatalogRouter] Song ID {song_id} not found for search")
        raise HTTPException(status_code=404, detail=f"Song ID {song_id} not found")

    engine_id = engine or DEFAULT_SEARCH_ENGINE

    search_service = SearchService()
    url = search_service.get_search_url(song, engine=engine_id)
    return {"url": url}


@router.post("/catalog/ingest/check", response_model=IngestionReportView)
async def check_ingestion(request: IngestionCheckRequest) -> IngestionReportView:
    """Performs a dry-run ingestion collision check."""
    logger.debug(f"[CatalogRouter] check_ingestion(path='{request.file_path}')")
    result = _get_service().check_ingestion(request.file_path)

    if result["status"] == "ERROR":
        logger.warning(f"[CatalogRouter] Ingestion check ERROR: {result['message']}")
        raise HTTPException(status_code=400, detail=result["message"])

    # Cast domain Song to SongView for the frontend contract
    if "song" in result and result["song"]:
        result["song"] = SongView.from_domain(result["song"])

    return IngestionReportView(**result)


@router.get("/validation-rules")
def get_validation_rules():
    """Returns scalar field validation rules for frontend use."""
    import datetime

    year_rules = SCALAR_VALIDATION["year"]
    return {
        "year": {
            "min": year_rules["min"],
            "max": datetime.date.today().year + year_rules["max_offset"],
        },
        "bpm": {
            "min": SCALAR_VALIDATION["bpm"]["min"],
            "max": SCALAR_VALIDATION["bpm"]["max"],
        },
        "isrc": {"pattern": SCALAR_VALIDATION["isrc"]["pattern"]},
        "tags": {
            "default_category": TAG_DEFAULT_CATEGORY,
            "delimiter": TAG_CATEGORY_DELIMITER,
            "input_format": TAG_INPUT_FORMAT,
        },
        "default_search_engine": DEFAULT_SEARCH_ENGINE,
        "credit_separators": DEFAULT_CREDIT_SEPARATORS,
    }
