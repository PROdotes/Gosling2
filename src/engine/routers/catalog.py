from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from src.models.view_models import (
    SongView,
    SongSlimView,
    AlbumSlimView,
    AlbumView,
    TagView,
    PublisherView,
    IdentityView,
    IdentitySlimView,
    ArtistChipView,
    IngestionCheckRequest,
    IngestionReportView,
)
from src.services.catalog_service import CatalogService
from src.services.logger import logger
from src.engine.config import (
    SCALAR_VALIDATION,
    TAG_DEFAULT_CATEGORY,
    TAG_CATEGORY_DELIMITER,
    TAG_INPUT_FORMAT,
    DEFAULT_SEARCH_ENGINE,
    DEFAULT_CREDIT_SEPARATORS,
    SCRUBBER_AUTO_PLAY,
    BLUR_SAVES_SCALARS,
    ID3_FRAMES_PATH,
)
from fastapi import Depends
from src.services.search_service import SearchService

router = APIRouter(prefix="/api/v1", tags=["catalog"])


def _get_service() -> CatalogService:
    """Centralized service factory for the router."""
    return CatalogService()


@router.get("/songs/filter-values")
async def get_filter_values(
    q: str = "",
    service: CatalogService = Depends(_get_service),
) -> dict:
    """Returns all distinct values for the filter sidebar, optionally filtered by search query."""
    return service.get_filter_values(q=q)


@router.get("/songs/filter", response_model=List[SongSlimView])
async def filter_songs(
    artists: Optional[List[str]] = Query(default=None),
    contributors: Optional[List[str]] = Query(default=None),
    years: Optional[List[int]] = Query(default=None),
    decades: Optional[List[int]] = Query(default=None),
    genres: Optional[List[str]] = Query(default=None),
    albums: Optional[List[str]] = Query(default=None),
    publishers: Optional[List[str]] = Query(default=None),
    statuses: Optional[List[str]] = Query(default=None),
    tags: Optional[List[str]] = Query(default=None),
    live_only: bool = False,
    has_original: bool = False,
    mode: str = "ALL",
    q: Optional[str] = None,
    service: CatalogService = Depends(_get_service),
) -> List[SongSlimView]:
    """Filter songs by sidebar criteria. Returns slim list-view models."""
    rows = service.filter_songs_slim(
        artists=artists,
        contributors=contributors,
        years=years,
        decades=decades,
        genres=genres,
        albums=albums,
        publishers=publishers,
        statuses=statuses,
        tags=tags,
        live_only=live_only,
        has_original=has_original,
        mode=mode,
        q=q,
    )
    return [SongSlimView.from_row(r) for r in rows]


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


@router.get("/songs/duplicates", response_model=List[List[int]])
async def get_duplicate_songs(
    service: CatalogService = Depends(_get_service),
) -> List[List[int]]:
    """
    Returns groups of song IDs that share the same MediaName (case-insensitive)
    and the same set of Performer identity IDs. Each group has >= 2 song IDs.
    Songs with no resolved performer identities are skipped.
    """
    groups = service.find_duplicate_songs()
    logger.debug(f"[CatalogRouter] get_duplicate_songs groups={len(groups)}")
    return groups


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

        # 1. Original source path — from StagingOrigins DB record only
        if view.estimated_original_path:
            import os
            if os.path.exists(view.estimated_original_path):
                view.original_exists = True

        # 2. Organized destination preview (May fail due to metadata error)
        try:
            from src.engine.config import LIBRARY_ROOT

            root = LIBRARY_ROOT
            preview = service._library_service._filing_service.evaluate_routing(song)
            view.projected_path = str(root / preview)
        except Exception as e:
            logger.debug(
                f"[CatalogRouter] Routing preview failed for song {song_id}: {e}"
            )
            view.projected_path = f"[Routing error] {e}"

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


@router.get("/identities", response_model=List[IdentitySlimView])
async def get_all_identities() -> List[IdentitySlimView]:
    """Fetch slim list-view rows for all active artists/identities."""
    logger.debug("[CatalogRouter] get_all_identities()")
    rows = _get_service().get_all_identities_slim()
    return [IdentitySlimView.from_row(r) for r in rows]


@router.get("/identities/search", response_model=List[IdentitySlimView])
async def search_identities(q: str, exclude_groups: bool = False) -> List[IdentitySlimView]:
    """Slim list-view search by DisplayName, LegalName, or Alias."""
    logger.debug(
        f"[CatalogRouter] search_identities(q='{q}', exclude_groups={exclude_groups})"
    )
    rows = _get_service().search_identities_slim(q, exclude_groups=exclude_groups)
    return [IdentitySlimView.from_row(r) for r in rows]


@router.get("/artist-names/search", response_model=List[ArtistChipView])
async def search_artist_names(q: str, exclude_groups: bool = False) -> List[ArtistChipView]:
    """Search ArtistNames for picker results. One row per name."""
    logger.debug(
        f"[CatalogRouter] search_artist_names(q='{q}', exclude_groups={exclude_groups})"
    )
    return _get_service().search_artist_names(q, exclude_groups=exclude_groups)


@router.get("/identities/{identity_id:int}/songs", response_model=List[SongSlimView])
async def get_songs_by_identity(identity_id: int) -> List[SongSlimView]:
    """Fetch slim song list for a full universal identity tree."""
    logger.debug(f"[CatalogRouter] get_songs_by_identity(id={identity_id})")

    identity = _get_service().get_identity(identity_id)
    if not identity:
        logger.warning(
            f"[CatalogRouter] VIOLATION: Identity ID {identity_id} not found"
        )
        raise HTTPException(
            status_code=404, detail=f"Identity ID {identity_id} not found"
        )

    rows = _get_service().get_songs_slim_by_identity(identity_id)
    return [SongSlimView.from_row(r) for r in rows]


@router.get("/identities/{identity_id:int}/albums", response_model=List[AlbumSlimView])
async def get_albums_by_identity(identity_id: int) -> List[AlbumSlimView]:
    """Fetch slim album list for an identity (across aliases, members, and groups)."""
    logger.debug(f"[CatalogRouter] get_albums_by_identity(id={identity_id})")

    identity = _get_service().get_identity(identity_id)
    if not identity:
        logger.warning(
            f"[CatalogRouter] VIOLATION: Identity ID {identity_id} not found"
        )
        raise HTTPException(
            status_code=404, detail=f"Identity ID {identity_id} not found"
        )

    rows = _get_service().get_albums_slim_by_identity(identity_id)
    return [AlbumSlimView.from_row(r) for r in rows]


@router.get("/publishers", response_model=List[PublisherView])
async def get_all_publishers() -> List[PublisherView]:
    """Fetch a list of all active music publishers."""
    logger.debug("[CatalogRouter] get_all_publishers()")
    service = _get_service()
    publishers = service.get_all_publishers()
    ids = [p.id for p in publishers if p.id is not None]
    counts = service.get_publisher_link_counts(ids)
    views = [PublisherView.model_validate(p.model_dump()) for p in publishers]
    for v in views:
        if v.id is not None:
            v.song_count = counts.get(v.id, {}).get("song_count", 0)
            v.album_count = counts.get(v.id, {}).get("album_count", 0)
    return views


@router.get("/publishers/search", response_model=List[PublisherView])
async def search_publishers(q: str) -> List[PublisherView]:
    """Search for publishers by name."""
    logger.debug(f"[CatalogRouter] search_publishers(q='{q}')")
    service = _get_service()
    publishers = service.search_publishers(q)
    ids = [p.id for p in publishers if p.id is not None]
    counts = service.get_publisher_link_counts(ids)
    views = [PublisherView.model_validate(p.model_dump()) for p in publishers]
    for v in views:
        if v.id is not None:
            v.song_count = counts.get(v.id, {}).get("song_count", 0)
            v.album_count = counts.get(v.id, {}).get("album_count", 0)
    return views


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


@router.get("/publishers/{publisher_id:int}/songs", response_model=List[SongSlimView])
async def get_songs_by_publisher(publisher_id: int) -> List[SongSlimView]:
    """Fetch slim song repertoire for a given publisher."""
    logger.debug(f"[CatalogRouter] get_songs_by_publisher(id={publisher_id})")
    pub = _get_service().get_publisher(publisher_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publisher not found")

    rows = _get_service().get_songs_slim_by_publisher(publisher_id)
    return [SongSlimView.from_row(r) for r in rows]


@router.delete("/publishers/{publisher_id:int}", status_code=204)
async def delete_publisher(publisher_id: int) -> None:
    """Soft-delete a single publisher. 404 if not found, 403 if linked to active songs or albums."""
    logger.debug(f"[CatalogRouter] delete_publisher(id={publisher_id})")
    service = _get_service()
    if not service.get_publisher(publisher_id):
        raise HTTPException(
            status_code=404, detail=f"Publisher {publisher_id} not found"
        )
    deleted = service.delete_unlinked_publishers([publisher_id])
    if deleted == 0:
        raise HTTPException(
            status_code=403,
            detail=f"Publisher {publisher_id} is linked to active songs or albums",
        )


@router.delete("/publishers", response_model=dict)
async def bulk_delete_unlinked_publishers(unlinked: bool = False) -> dict:
    """Soft-delete all unlinked publishers. Requires ?unlinked=true as a safety flag."""
    logger.debug(
        f"[CatalogRouter] bulk_delete_unlinked_publishers(unlinked={unlinked})"
    )
    if not unlinked:
        raise HTTPException(
            status_code=400, detail="Pass ?unlinked=true to confirm bulk delete"
        )
    service = _get_service()
    all_publishers = service.get_all_publishers()
    deleted = service.delete_unlinked_publishers(
        [p.id for p in all_publishers if p.id is not None]
    )
    return {"deleted": deleted}


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


@router.delete("/albums/{album_id:int}", status_code=204)
async def delete_album(album_id: int) -> None:
    """Soft-delete a single album. 404 if not found, 403 if linked to active songs."""
    logger.debug(f"[CatalogRouter] delete_album(id={album_id})")
    service = _get_service()
    if not service.get_album(album_id):
        raise HTTPException(status_code=404, detail=f"Album {album_id} not found")
    deleted = service.delete_unlinked_albums([album_id])
    if deleted == 0:
        raise HTTPException(
            status_code=403, detail=f"Album {album_id} is linked to active songs"
        )


@router.delete("/albums", response_model=dict)
async def bulk_delete_unlinked_albums(unlinked: bool = False) -> dict:
    """Soft-delete all unlinked albums. Requires ?unlinked=true as a safety flag."""
    logger.debug(f"[CatalogRouter] bulk_delete_unlinked_albums(unlinked={unlinked})")
    if not unlinked:
        raise HTTPException(
            status_code=400, detail="Pass ?unlinked=true to confirm bulk delete"
        )
    service = _get_service()
    all_albums = service.get_all_albums()
    deleted = service.delete_unlinked_albums(
        [a.id for a in all_albums if a.id is not None]
    )
    return {"deleted": deleted}


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


@router.get("/tags/{tag_id:int}/songs", response_model=List[SongSlimView])
async def get_songs_by_tag(tag_id: int) -> List[SongSlimView]:
    """Fetch slim song list linked to this tag."""
    logger.debug(f"[CatalogRouter] get_songs_by_tag(id={tag_id})")
    tag = _get_service().get_tag(tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    rows = _get_service().get_songs_slim_by_tag(tag_id)
    return [SongSlimView.from_row(r) for r in rows]


@router.delete("/tags/{tag_id:int}", status_code=204)
async def delete_tag(tag_id: int) -> None:
    """Soft-delete a single tag. 404 if not found, 403 if linked to active songs."""
    logger.debug(f"[CatalogRouter] delete_tag(id={tag_id})")
    service = _get_service()
    if not service.get_tag(tag_id):
        raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")
    deleted = service.delete_unlinked_tags([tag_id])
    if deleted == 0:
        raise HTTPException(
            status_code=403, detail=f"Tag {tag_id} is linked to active songs"
        )


@router.delete("/tags", response_model=dict)
async def bulk_delete_unlinked_tags(unlinked: bool = False) -> dict:
    """Soft-delete all unlinked tags. Requires ?unlinked=true as a safety flag."""
    logger.debug(f"[CatalogRouter] bulk_delete_unlinked_tags(unlinked={unlinked})")
    if not unlinked:
        raise HTTPException(
            status_code=400, detail="Pass ?unlinked=true to confirm bulk delete"
        )
    service = _get_service()
    all_tags = service.get_all_tags()
    deleted = service.delete_unlinked_tags([t.id for t in all_tags if t.id is not None])
    return {"deleted": deleted}


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


@router.get("/config")
def get_config():
    """Returns application configuration settings."""
    from src.engine.config import ProcessingStatus, TAG_DEFAULT_CATEGORY

    return {
        "search_engines": SearchService.ENGINES,
        "default_search_engine": DEFAULT_SEARCH_ENGINE,
        "processing_status": {s.name: s.value for s in ProcessingStatus},
        "tag_default_category": TAG_DEFAULT_CATEGORY,
    }


def _load_tag_category_colors() -> dict:
    import json

    try:
        with open(ID3_FRAMES_PATH) as f:
            frames = json.load(f)
        colors = {}
        for v in frames.values():
            if isinstance(v, dict) and "tag_category" in v and "color" in v:
                cat = v["tag_category"]
                if cat not in colors:
                    colors[cat] = v["color"]
        return colors
    except Exception:
        return {}


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
            "category_colors": _load_tag_category_colors(),
        },
        "default_search_engine": DEFAULT_SEARCH_ENGINE,
        "search_engines": SearchService.ENGINES,
        "credit_separators": DEFAULT_CREDIT_SEPARATORS,
        "scrubber_auto_play": SCRUBBER_AUTO_PLAY,
        "blur_saves_scalars": BLUR_SAVES_SCALARS,
    }
