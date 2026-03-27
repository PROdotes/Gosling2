from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from src.services.catalog_service import CatalogService
from src.models.domain import SongCredit, Tag, Publisher, SongAlbum, Album
from src.engine.config import get_db_path

router = APIRouter(prefix="/api/v1", tags=["song-updates"])


def _get_service() -> CatalogService:
    return CatalogService(get_db_path())


def _require_song(song_id: int, service: CatalogService):
    if not service.get_song(song_id):
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")


def _require_album(album_id: int, service: CatalogService):
    if not service.get_album(album_id):
        raise HTTPException(status_code=404, detail=f"Album {album_id} not found")


# --- Request Bodies ---

class SongScalarUpdate(BaseModel):
    media_name: Optional[str] = None
    year: Optional[int] = None
    bpm: Optional[int] = None
    isrc: Optional[str] = None
    notes: Optional[str] = None


class AddCreditBody(BaseModel):
    display_name: str
    role_name: str


class UpdateCreditNameBody(BaseModel):
    display_name: str


class AddAlbumBody(BaseModel):
    album_id: Optional[int] = None
    title: Optional[str] = None
    album_type: Optional[str] = None
    release_year: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None


class UpdateAlbumLinkBody(BaseModel):
    track_number: Optional[int] = None
    disc_number: Optional[int] = None


class UpdateAlbumBody(BaseModel):
    title: Optional[str] = None
    album_type: Optional[str] = None
    release_year: Optional[int] = None


class AddAlbumCreditBody(BaseModel):
    artist_name: str


class SetAlbumPublisherBody(BaseModel):
    publisher_name: str


class AddTagBody(BaseModel):
    tag_name: str
    category: str


class UpdateTagBody(BaseModel):
    tag_name: str
    category: str


class AddPublisherBody(BaseModel):
    publisher_name: str


class UpdatePublisherBody(BaseModel):
    publisher_name: str


# --- Scalar ---

@router.patch("/songs/{song_id}")
async def update_song_scalars(
    song_id: int,
    body: SongScalarUpdate,
    service: CatalogService = Depends(_get_service),
):
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=422, detail="No fields provided")
    try:
        song = service.update_song_scalars(song_id, fields)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return song


# --- Credits ---

@router.post("/songs/{song_id}/credits", response_model=SongCredit)
async def add_song_credit(
    song_id: int,
    body: AddCreditBody,
    service: CatalogService = Depends(_get_service),
):
    _require_song(song_id, service)
    try:
        credit = service.add_song_credit(song_id, body.display_name, body.role_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return credit


@router.delete("/songs/{song_id}/credits/{credit_id}", status_code=204)
async def remove_song_credit(
    song_id: int,
    credit_id: int,
    service: CatalogService = Depends(_get_service),
):
    song = service.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    if not any(c.credit_id == credit_id for c in song.credits):
        raise HTTPException(status_code=404, detail=f"Credit {credit_id} not found on song {song_id}")
    try:
        service.remove_song_credit(song_id, credit_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/songs/{song_id}/credits/{name_id}", status_code=204)
async def update_credit_name(
    song_id: int,
    name_id: int,
    body: UpdateCreditNameBody,
    service: CatalogService = Depends(_get_service),
):
    try:
        service.update_credit_name(name_id, body.display_name)
    except LookupError:
        raise HTTPException(status_code=404, detail="Credit name not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Albums ---

@router.post("/songs/{song_id}/albums", response_model=SongAlbum)
async def add_song_album(
    song_id: int,
    body: AddAlbumBody,
    service: CatalogService = Depends(_get_service),
):
    _require_song(song_id, service)
    try:
        if body.album_id is not None:
            link = service.add_song_album(
                song_id, body.album_id, body.track_number, body.disc_number
            )
        elif body.title:
            album_data = {}
            if body.title:
                album_data["title"] = body.title
            if body.album_type:
                album_data["album_type"] = body.album_type
            if body.release_year:
                album_data["release_year"] = body.release_year
            link = service.create_and_link_album(
                song_id, album_data, body.track_number, body.disc_number
            )
        else:
            raise HTTPException(
                status_code=422, detail="Provide album_id or title"
            )
    except HTTPException:
        raise
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return link


@router.delete("/songs/{song_id}/albums/{album_id}", status_code=204)
async def remove_song_album(
    song_id: int,
    album_id: int,
    service: CatalogService = Depends(_get_service),
):
    song = service.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    if not any(a.album_id == album_id for a in song.albums):
        raise HTTPException(status_code=404, detail=f"Album link {album_id} not found on song {song_id}")
    try:
        service.remove_song_album(song_id, album_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/songs/{song_id}/albums/{album_id}", status_code=204)
async def update_song_album_link(
    song_id: int,
    album_id: int,
    body: UpdateAlbumLinkBody,
    service: CatalogService = Depends(_get_service),
):
    song = service.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    if not any(a.album_id == album_id for a in song.albums):
        raise HTTPException(status_code=404, detail=f"Album link {album_id} not found on song {song_id}")
    try:
        service.update_song_album_link(
            song_id, album_id, body.track_number, body.disc_number
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/albums/{album_id}", response_model=Album)
async def update_album(
    album_id: int,
    body: UpdateAlbumBody,
    service: CatalogService = Depends(_get_service),
):
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=422, detail="No fields provided")
    try:
        album = service.update_album(album_id, fields)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Album {album_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return album


@router.post("/albums/{album_id}/credits", status_code=204)
async def add_album_credit(
    album_id: int,
    body: AddAlbumCreditBody,
    service: CatalogService = Depends(_get_service),
):
    _require_album(album_id, service)
    try:
        service.add_album_credit(album_id, body.artist_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/albums/{album_id}/credits/{name_id}", status_code=204)
async def remove_album_credit(
    album_id: int,
    name_id: int,
    service: CatalogService = Depends(_get_service),
):
    album = service.get_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail=f"Album {album_id} not found")
    if not any(c.name_id == name_id for c in album.credits):
        raise HTTPException(status_code=404, detail=f"Credit {name_id} not found on album {album_id}")
    try:
        service.remove_album_credit(album_id, name_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/albums/{album_id}/publisher", status_code=204)
async def set_album_publisher(
    album_id: int,
    body: SetAlbumPublisherBody,
    service: CatalogService = Depends(_get_service),
):
    _require_album(album_id, service)
    try:
        service.update_album_publisher(album_id, body.publisher_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Tags ---

@router.post("/songs/{song_id}/tags", response_model=Tag)
async def add_song_tag(
    song_id: int,
    body: AddTagBody,
    service: CatalogService = Depends(_get_service),
):
    _require_song(song_id, service)
    try:
        tag = service.add_song_tag(song_id, body.tag_name, body.category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return tag


@router.delete("/songs/{song_id}/tags/{tag_id}", status_code=204)
async def remove_song_tag(
    song_id: int,
    tag_id: int,
    service: CatalogService = Depends(_get_service),
):
    song = service.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    if not any(t.id == tag_id for t in song.tags):
        raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found on song {song_id}")
    try:
        service.remove_song_tag(song_id, tag_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tags/{tag_id}", status_code=204)
async def update_tag(
    tag_id: int,
    body: UpdateTagBody,
    service: CatalogService = Depends(_get_service),
):
    if not service.get_tag(tag_id):
        raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")
    try:
        service.update_tag(tag_id, body.tag_name, body.category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Publishers ---

@router.post("/songs/{song_id}/publishers", response_model=Publisher)
async def add_song_publisher(
    song_id: int,
    body: AddPublisherBody,
    service: CatalogService = Depends(_get_service),
):
    _require_song(song_id, service)
    try:
        publisher = service.add_song_publisher(song_id, body.publisher_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return publisher


@router.delete("/songs/{song_id}/publishers/{publisher_id}", status_code=204)
async def remove_song_publisher(
    song_id: int,
    publisher_id: int,
    service: CatalogService = Depends(_get_service),
):
    song = service.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    if not any(p.id == publisher_id for p in song.publishers):
        raise HTTPException(status_code=404, detail=f"Publisher {publisher_id} not found on song {song_id}")
    try:
        service.remove_song_publisher(song_id, publisher_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/publishers/{publisher_id}", status_code=204)
async def update_publisher(
    publisher_id: int,
    body: UpdatePublisherBody,
    service: CatalogService = Depends(_get_service),
):
    if not service.get_publisher(publisher_id):
        raise HTTPException(status_code=404, detail=f"Publisher {publisher_id} not found")
    try:
        service.update_publisher(publisher_id, body.publisher_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
