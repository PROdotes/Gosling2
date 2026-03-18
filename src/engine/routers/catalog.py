from fastapi import APIRouter, HTTPException
from typing import List, Optional
from src.models.domain import Publisher
from src.models.view_models import SongView, IdentityView, AlbumView
from src.services.catalog_service import CatalogService
from src.services.logger import logger
import os

router = APIRouter(prefix="/api/v1", tags=["catalog"])


def _get_service() -> CatalogService:
    """Centralized service factory for the router."""
    db_path = os.getenv("GOSLING_DB_PATH", "sqldb/gosling2.db")
    return CatalogService(db_path)


@router.get("/songs/search", response_model=List[SongView])
async def search_songs(
    q: Optional[str] = None, query: Optional[str] = None
) -> List[SongView]:
    """Search for songs by title match. Supports both 'q' and 'query'."""
    search_term = q or query
    logger.info(f"[CatalogRouter] GET /songs/search search_term='{search_term}'")

    # We allow empty/short queries to explore the DB
    results = _get_service().search_songs(search_term or "")
    logger.debug(f"[CatalogRouter] Found {len(results)} search results.")
    return [SongView.from_domain(s) for s in results]


@router.get("/songs/{song_id:int}", response_model=SongView)
async def get_song(song_id: int) -> SongView:
    """Fetch a single song by ID."""
    logger.debug(f"[CatalogRouter] GET /songs/{song_id}")
    song = _get_service().get_song(song_id)
    if not song:
        logger.warning(f"[CatalogRouter] VIOLATION: Song ID {song_id} not found")
        raise HTTPException(status_code=404, detail=f"Song ID {song_id} not found")
    return SongView.from_domain(song)


@router.get("/identities/{identity_id:int}", response_model=IdentityView)
async def get_identity(identity_id: int) -> IdentityView:
    """Fetch a full identity tree by ID."""
    logger.debug(f"[CatalogRouter] GET /identities/{identity_id}")
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
    logger.debug("[CatalogRouter] GET /identities")
    identities = _get_service().get_all_identities()
    return [IdentityView.from_domain(i) for i in identities]


@router.get("/identities/search", response_model=List[IdentityView])
async def search_identities(q: str) -> List[IdentityView]:
    """Search for identities by name or alias."""
    logger.debug(f"[CatalogRouter] GET /identities/search q='{q}'")
    identities = _get_service().search_identities(q)
    return [IdentityView.from_domain(i) for i in identities]


@router.get("/identities/{identity_id:int}/songs", response_model=List[SongView])
async def get_songs_by_identity(identity_id: int) -> List[SongView]:
    """Fetch all complete songs associated with a full universal identity tree."""
    logger.debug(f"[CatalogRouter] GET /identities/{identity_id}/songs")

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


@router.get("/publishers", response_model=List[Publisher])
async def get_all_publishers() -> List[Publisher]:
    """Fetch a list of all active music publishers."""
    logger.debug("[CatalogRouter] GET /publishers")
    return _get_service().get_all_publishers()


@router.get("/publishers/search", response_model=List[Publisher])
async def search_publishers(q: str) -> List[Publisher]:
    """Search for publishers by name."""
    logger.debug(f"[CatalogRouter] GET /publishers/search q='{q}'")
    return _get_service().search_publishers(q)


@router.get("/publishers/{publisher_id:int}", response_model=Publisher)
async def get_publisher(publisher_id: int) -> Publisher:
    """Fetch a single publisher by ID."""
    logger.debug(f"[CatalogRouter] GET /publishers/{publisher_id}")
    publisher = _get_service().get_publisher(publisher_id)
    if not publisher:
        logger.warning(
            f"[CatalogRouter] VIOLATION: Publisher ID {publisher_id} not found"
        )
        raise HTTPException(
            status_code=404, detail=f"Publisher ID {publisher_id} not found"
        )
    return publisher


@router.get("/publishers/{publisher_id:int}/songs", response_model=List[SongView])
async def get_publisher_songs(publisher_id: int) -> List[SongView]:
    """Fetch the full repertoire associated with a given publisher."""
    logger.debug(f"[CatalogRouter] GET /publishers/{publisher_id}/songs")
    # Verify existence
    pub = _get_service().get_publisher(publisher_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publisher not found")

    songs = _get_service().get_publisher_songs(publisher_id)
    return [SongView.from_domain(s) for s in songs]


@router.get("/albums", response_model=List[AlbumView])
async def get_all_albums() -> List[AlbumView]:
    """Fetch a list of all albums."""
    logger.debug("[CatalogRouter] GET /albums")
    albums = _get_service().get_all_albums()
    return [AlbumView.from_domain(album) for album in albums]


@router.get("/albums/search", response_model=List[AlbumView])
async def search_albums(q: str) -> List[AlbumView]:
    """Search albums by title."""
    logger.debug(f"[CatalogRouter] GET /albums/search q='{q}'")
    albums = _get_service().search_albums(q)
    return [AlbumView.from_domain(album) for album in albums]


@router.get("/albums/{album_id:int}", response_model=AlbumView)
async def get_album(album_id: int) -> AlbumView:
    """Fetch a single album by ID."""
    logger.debug(f"[CatalogRouter] GET /albums/{album_id}")
    album = _get_service().get_album(album_id)
    if not album:
        logger.warning(f"[CatalogRouter] VIOLATION: Album ID {album_id} not found")
        raise HTTPException(status_code=404, detail=f"Album ID {album_id} not found")

    # Satisfaction for Pyright: proven non-None by raising above
    return AlbumView.from_domain(album)
