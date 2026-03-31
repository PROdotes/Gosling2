from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from src.engine.config import ALBUM_DEFAULT_TYPE
from src.services.catalog_service import CatalogService
from src.services.logger import logger
from src.models.domain import SongCredit, Tag, Publisher, SongAlbum, Album, AlbumCredit
from src.models.view_models import (
    SongView,
    SongScalarUpdate,
    AddCreditBody,
    UpdateCreditNameBody,
    AddAlbumBody,
    UpdateAlbumLinkBody,
    UpdateAlbumBody,
    AddAlbumCreditBody,
    AddTagBody,
    UpdateTagBody,
    AddPublisherBody,
    UpdatePublisherBody,
    SetPublisherParentBody,
)
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

    logger.debug(
        f"[SongUpdates] -> update_song_scalars(id={song_id}, keys={list(fields.keys())})"
    )
    try:
        song = service.update_song_scalars(song_id, fields)
        logger.debug(f"[SongUpdates] <- update_song_scalars(id={song_id}) OK")
        return SongView.from_domain(song)
    except ValueError as e:
        logger.warning(
            f"[SongUpdates] <- update_song_scalars(id={song_id}) VAL_ERROR: {e}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError:
        logger.warning(f"[SongUpdates] <- update_song_scalars(id={song_id}) NOT_FOUND")
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    except Exception as e:
        logger.error(
            f"[SongUpdates] <- update_song_scalars(id={song_id}) CRITICAL: {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# --- Roles ---


@router.get("/roles")
async def get_all_roles(service: CatalogService = Depends(_get_service)):
    return service.get_all_roles()


# --- Credits ---


@router.post("/songs/{song_id}/credits", response_model=SongCredit)
async def add_song_credit(
    song_id: int,
    body: AddCreditBody,
    service: CatalogService = Depends(_get_service),
):
    _require_song(song_id, service)
    logger.debug(
        f"[SongUpdates] -> add_song_credit(id={song_id}, name='{body.display_name}', role='{body.role_name}')"
    )
    try:
        credit = service.add_song_credit(
            song_id, body.display_name, body.role_name, identity_id=body.identity_id
        )
        logger.debug(f"[SongUpdates] <- add_song_credit(id={song_id}) OK")
        return credit
    except ValueError as e:
        logger.warning(f"[SongUpdates] <- add_song_credit VAL_ERROR: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[SongUpdates] <- add_song_credit CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/songs/{song_id}/credits/{credit_id}", status_code=204)
async def remove_song_credit(
    song_id: int,
    credit_id: int,
    service: CatalogService = Depends(_get_service),
):
    logger.debug(
        f"[SongUpdates] -> remove_song_credit(id={song_id}, credit_id={credit_id})"
    )
    song = service.get_song(song_id)
    if not song:
        logger.warning(f"[SongUpdates] <- remove_song_credit NOT_FOUND song={song_id}")
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")

    if not any(c.credit_id == credit_id for c in song.credits):
        logger.warning(
            f"[SongUpdates] <- remove_song_credit NOT_FOUND credit={credit_id} on song={song_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Credit {credit_id} not found on song {song_id}"
        )

    try:
        service.remove_song_credit(song_id, credit_id)
        logger.debug("[SongUpdates] <- remove_song_credit OK")
    except Exception as e:
        logger.error(f"[SongUpdates] <- remove_song_credit CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/songs/{song_id}/credits/{name_id}", status_code=204)
async def update_credit_name(
    song_id: int,
    name_id: int,
    body: UpdateCreditNameBody,
    service: CatalogService = Depends(_get_service),
):
    logger.debug(
        f"[SongUpdates] -> update_credit_name(id={name_id}, name='{body.display_name}')"
    )
    try:
        service.update_credit_name(name_id, body.display_name)
        logger.debug("[SongUpdates] <- update_credit_name OK")
    except LookupError:
        logger.warning(f"[SongUpdates] <- update_credit_name NOT_FOUND id={name_id}")
        raise HTTPException(status_code=404, detail="Credit name not found")
    except Exception as e:
        logger.error(f"[SongUpdates] <- update_credit_name CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Albums ---


@router.post("/songs/{song_id}/albums", response_model=SongAlbum)
async def add_song_album(
    song_id: int,
    body: AddAlbumBody,
    service: CatalogService = Depends(_get_service),
) -> SongAlbum:
    _require_song(song_id, service)
    try:
        if body.album_id is not None:
            logger.debug(
                f"[SongUpdates] -> add_song_album LINK_EXISTING(id={song_id}, album_id={body.album_id})"
            )
            link = service.add_song_album(
                song_id, body.album_id, body.track_number, body.disc_number
            )
            logger.debug("[SongUpdates] <- add_song_album OK")
            return link
        elif body.title:
            logger.debug(
                f"[SongUpdates] -> add_song_album CREATE_AND_LINK(id={song_id}, title='{body.title}')"
            )
            album_data: dict[str, Any] = {
                "title": body.title,
                "album_type": body.album_type or ALBUM_DEFAULT_TYPE,
            }
            if body.release_year:
                album_data["release_year"] = body.release_year

            link = service.create_and_link_album(
                song_id, album_data, body.track_number, body.disc_number
            )
            logger.debug("[SongUpdates] <- add_song_album OK")
            return link
        else:
            logger.warning(
                "[SongUpdates] <- add_song_album VALIDATION_FAILED (no id/title)"
            )
            raise HTTPException(status_code=422, detail="Provide album_id or title")
    except HTTPException:
        raise
    except LookupError:
        logger.warning(f"[SongUpdates] <- add_song_album NOT_FOUND id={song_id}")
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    except ValueError as e:
        logger.warning(f"[SongUpdates] <- add_song_album VAL_ERROR: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[SongUpdates] <- add_song_album CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/songs/{song_id}/albums/{album_id}", status_code=204)
async def remove_song_album(
    song_id: int,
    album_id: int,
    service: CatalogService = Depends(_get_service),
):
    logger.debug(
        f"[SongUpdates] -> remove_song_album(id={song_id}, album_id={album_id})"
    )
    song = service.get_song(song_id)
    if not song:
        logger.warning(f"[SongUpdates] <- remove_song_album NOT_FOUND song={song_id}")
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")

    if not any(a.album_id == album_id for a in song.albums):
        logger.warning(
            f"[SongUpdates] <- remove_song_album NOT_FOUND link={album_id} on song={song_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Album link {album_id} not found on song {song_id}"
        )

    try:
        service.remove_song_album(song_id, album_id)
        logger.debug("[SongUpdates] <- remove_song_album OK")
    except Exception as e:
        logger.error(f"[SongUpdates] <- remove_song_album CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/songs/{song_id}/albums/{album_id}", status_code=204)
async def update_song_album_link(
    song_id: int,
    album_id: int,
    body: UpdateAlbumLinkBody,
    service: CatalogService = Depends(_get_service),
):
    logger.debug(
        f"[SongUpdates] -> update_song_album_link(id={song_id}, album_id={album_id}, fields={body.model_dump(exclude_none=True)})"
    )
    song = service.get_song(song_id)
    if not song:
        logger.warning(
            f"[SongUpdates] <- update_song_album_link NOT_FOUND song={song_id}"
        )
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")

    if not any(a.album_id == album_id for a in song.albums):
        logger.warning(
            f"[SongUpdates] <- update_song_album_link NOT_FOUND link={album_id} on song={song_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Album link {album_id} not found on song {song_id}"
        )

    try:
        service.update_song_album_link(
            song_id, album_id, body.track_number, body.disc_number
        )
        logger.debug("[SongUpdates] <- update_song_album_link OK")
    except ValueError as e:
        logger.warning(f"[SongUpdates] <- update_song_album_link VAL_ERROR: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[SongUpdates] <- update_song_album_link CRITICAL: {e}")
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

    logger.debug(
        f"[SongUpdates] -> update_album(id={album_id}, keys={list(fields.keys())})"
    )
    try:
        album = service.update_album(album_id, fields)
        logger.debug("[SongUpdates] <- update_album OK")
        return album
    except LookupError:
        logger.warning(f"[SongUpdates] <- update_album NOT_FOUND id={album_id}")
        raise HTTPException(status_code=404, detail=f"Album {album_id} not found")
    except Exception as e:
        logger.error(f"[SongUpdates] <- update_album CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/albums/{album_id}/credits", response_model=AlbumCredit)
async def add_album_credit(
    album_id: int,
    body: AddAlbumCreditBody,
    service: CatalogService = Depends(_get_service),
) -> AlbumCredit:
    _require_album(album_id, service)
    logger.debug(
        f"[SongUpdates] -> add_album_credit(id={album_id}, name='{body.display_name}', role='{body.role_name}')"
    )
    try:
        name_id = service.add_album_credit(
            album_id, body.display_name, body.role_name or "Performer", body.identity_id
        )
        album = service.get_album(album_id)
        if not album:
            raise HTTPException(status_code=500, detail="Album not found after adding credit")
        credit = next((c for c in album.credits if c.name_id == name_id), None)
        if not credit:
            raise HTTPException(status_code=500, detail="Credit created but not retrievable")
        logger.debug("[SongUpdates] <- add_album_credit OK")
        return credit
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SongUpdates] <- add_album_credit CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/albums/{album_id}/credits/{name_id}", status_code=204)
async def remove_album_credit(
    album_id: int,
    name_id: int,
    service: CatalogService = Depends(_get_service),
):
    logger.debug(
        f"[SongUpdates] -> remove_album_credit(id={album_id}, name_id={name_id})"
    )
    album = service.get_album(album_id)
    if not album:
        logger.warning(f"[SongUpdates] <- remove_album_credit NOT_FOUND id={album_id}")
        raise HTTPException(status_code=404, detail=f"Album {album_id} not found")

    if not any(c.name_id == name_id for c in album.credits):
        logger.warning(
            f"[SongUpdates] <- remove_album_credit NOT_FOUND credit={name_id} on album={album_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Credit {name_id} not found on album {album_id}"
        )

    try:
        service.remove_album_credit(album_id, name_id)
        logger.debug("[SongUpdates] <- remove_album_credit OK")
    except Exception as e:
        logger.error(f"[SongUpdates] <- remove_album_credit CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/albums/{album_id}/publishers", response_model=Publisher)
async def add_album_publisher(
    album_id: int,
    body: AddPublisherBody,
    service: CatalogService = Depends(_get_service),
):
    _require_album(album_id, service)
    logger.debug(
        f"[SongUpdates] -> add_album_publisher(id={album_id}, pub='{body.publisher_name}')"
    )
    try:
        publisher = service.add_album_publisher(album_id, body.publisher_name, body.publisher_id)
        logger.debug(f"[SongUpdates] <- add_album_publisher OK id={publisher.id}")
        return publisher
    except Exception as e:
        logger.error(f"[SongUpdates] <- add_album_publisher CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/albums/{album_id}/publishers/{publisher_id}", status_code=204)
async def remove_album_publisher(
    album_id: int,
    publisher_id: int,
    service: CatalogService = Depends(_get_service),
):
    _require_album(album_id, service)
    logger.debug(
        f"[SongUpdates] -> remove_album_publisher(id={album_id}, pub_id={publisher_id})"
    )
    try:
        service.remove_album_publisher(album_id, publisher_id)
        logger.debug("[SongUpdates] <- remove_album_publisher OK")
    except Exception as e:
        logger.error(f"[SongUpdates] <- remove_album_publisher CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Tags ---


@router.post("/songs/{song_id}/tags", response_model=Tag)
async def add_song_tag(
    song_id: int,
    body: AddTagBody,
    service: CatalogService = Depends(_get_service),
):
    _require_song(song_id, service)
    logger.debug(f"[SongUpdates] -> add_song_tag(id={song_id}, tag='{body.tag_name}')")
    try:
        tag = service.add_song_tag(song_id, body.tag_name, body.category, body.tag_id)
        logger.debug("[SongUpdates] <- add_song_tag OK")
        return tag
    except Exception as e:
        logger.error(f"[SongUpdates] <- add_song_tag CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/songs/{song_id}/tags/{tag_id}", status_code=204)
async def remove_song_tag(
    song_id: int,
    tag_id: int,
    service: CatalogService = Depends(_get_service),
):
    logger.debug(f"[SongUpdates] -> remove_song_tag(id={song_id}, tag_id={tag_id})")
    song = service.get_song(song_id)
    if not song:
        logger.warning(f"[SongUpdates] <- remove_song_tag NOT_FOUND song={song_id}")
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")

    if not any(t.id == tag_id for t in song.tags):
        logger.warning(
            f"[SongUpdates] <- remove_song_tag NOT_FOUND tag={tag_id} on song={song_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Tag {tag_id} not found on song {song_id}"
        )

    try:
        service.remove_song_tag(song_id, tag_id)
        logger.debug("[SongUpdates] <- remove_song_tag OK")
    except Exception as e:
        logger.error(f"[SongUpdates] <- remove_song_tag CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tags/{tag_id}", status_code=204)
async def update_tag(
    tag_id: int,
    body: UpdateTagBody,
    service: CatalogService = Depends(_get_service),
):
    logger.debug(f"[SongUpdates] -> update_tag(id={tag_id}, name='{body.tag_name}')")
    if not service.get_tag(tag_id):
        logger.warning(f"[SongUpdates] <- update_tag NOT_FOUND id={tag_id}")
        raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")
    try:
        service.update_tag(tag_id, body.tag_name, body.category)
        logger.debug("[SongUpdates] <- update_tag OK")
    except Exception as e:
        logger.error(f"[SongUpdates] <- update_tag CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Publishers ---


@router.post("/songs/{song_id}/publishers", response_model=Publisher)
async def add_song_publisher(
    song_id: int,
    body: AddPublisherBody,
    service: CatalogService = Depends(_get_service),
):
    _require_song(song_id, service)
    logger.debug(
        f"[SongUpdates] -> add_song_publisher(id={song_id}, pub='{body.publisher_name}')"
    )
    try:
        # Pass the optional ID to ensure Truth-First identity linking
        publisher = service.add_song_publisher(
            song_id, body.publisher_name, body.publisher_id
        )
        logger.debug(f"[SongUpdates] <- add_song_publisher OK id={publisher.id}")
        return publisher
    except Exception as e:
        logger.error(f"[SongUpdates] <- add_song_publisher CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/songs/{song_id}/publishers/{publisher_id}", status_code=204)
async def remove_song_publisher(
    song_id: int,
    publisher_id: int,
    service: CatalogService = Depends(_get_service),
):
    logger.debug(
        f"[SongUpdates] -> remove_song_publisher(id={song_id}, pub_id={publisher_id})"
    )
    song = service.get_song(song_id)
    if not song:
        logger.warning(
            f"[SongUpdates] <- remove_song_publisher NOT_FOUND song={song_id}"
        )
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")

    if not any(p.id == publisher_id for p in song.publishers):
        logger.warning(
            f"[SongUpdates] <- remove_song_publisher NOT_FOUND link={publisher_id} on song={song_id}"
        )
        raise HTTPException(
            status_code=404,
            detail=f"Publisher {publisher_id} not found on song {song_id}",
        )

    try:
        service.remove_song_publisher(song_id, publisher_id)
        logger.debug("[SongUpdates] <- remove_song_publisher OK")
    except Exception as e:
        logger.error(f"[SongUpdates] <- remove_song_publisher CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/publishers/{publisher_id}", status_code=204)
async def update_publisher(
    publisher_id: int,
    body: UpdatePublisherBody,
    service: CatalogService = Depends(_get_service),
):
    logger.debug(
        f"[SongUpdates] -> update_publisher(id={publisher_id}, name='{body.publisher_name}')"
    )
    if not service.get_publisher(publisher_id):
        logger.warning(f"[SongUpdates] <- update_publisher NOT_FOUND id={publisher_id}")
        raise HTTPException(
            status_code=404, detail=f"Publisher {publisher_id} not found"
        )
    try:
        service.update_publisher(publisher_id, body.publisher_name)
        logger.debug("[SongUpdates] <- update_publisher OK")
    except Exception as e:
        logger.error(f"[SongUpdates] <- update_publisher CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/publishers/{publisher_id}/parent", status_code=204)
async def set_publisher_parent(
    publisher_id: int,
    body: SetPublisherParentBody,
    service: CatalogService = Depends(_get_service),
):
    logger.debug(
        f"[SongUpdates] -> set_publisher_parent(id={publisher_id}, parent_id={body.parent_id})"
    )
    if not service.get_publisher(publisher_id):
        logger.warning(
            f"[SongUpdates] <- set_publisher_parent NOT_FOUND id={publisher_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Publisher {publisher_id} not found"
        )
    if body.parent_id is not None and not service.get_publisher(body.parent_id):
        logger.warning(
            f"[SongUpdates] <- set_publisher_parent NOT_FOUND parent_id={body.parent_id}"
        )
        raise HTTPException(
            status_code=404, detail=f"Parent publisher {body.parent_id} not found"
        )
    try:
        service.set_publisher_parent(publisher_id, body.parent_id)
        logger.debug("[SongUpdates] <- set_publisher_parent OK")
    except LookupError as e:
        logger.warning(f"[SongUpdates] <- set_publisher_parent NOT_FOUND: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[SongUpdates] <- set_publisher_parent CRITICAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))
