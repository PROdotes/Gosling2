from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.services.library_service import LibraryService
from src.engine.config import ALBUM_DEFAULT_TYPE, get_db_path

router = APIRouter(prefix="/api/v1/albums", tags=["albums", "write"])


def _get_library() -> LibraryService:
    return LibraryService(get_db_path())


def _sync_diff(song, album_id: int, album) -> dict:
    add = []
    update = []

    if not album.release_year and song.year:
        update.append({"type": "album", "id": album_id, "release_year": song.year})

    existing_name_ids = {c.name_id for c in (album.credits or [])}
    for credit in song.credits or []:
        if credit.role_name == "Performer" and credit.name_id not in existing_name_ids:
            add.append(
                {
                    "type": "credit",
                    "album_id": album_id,
                    "name": credit.display_name,
                    "id": credit.identity_id,
                    "role": "Performer",
                }
            )

    existing_pub_ids = {p.id for p in (album.publishers or [])}
    for pub in song.publishers or []:
        if pub.id not in existing_pub_ids:
            add.append(
                {
                    "type": "publisher",
                    "album_id": album_id,
                    "name": pub.name,
                    "id": pub.id,
                }
            )

    result = {}
    if add:
        result["add"] = add
    if update:
        result["update"] = update
    return result


@router.get("/{album_id}/sync-from-song/{song_id}")
async def sync_album_from_song_diff(
    album_id: int,
    song_id: int,
    library: LibraryService = Depends(_get_library),
) -> dict:
    """Returns the add/update payload to sync an existing album from a song. Does not write."""
    song = library.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    album = library.get_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail=f"Album {album_id} not found")
    return _sync_diff(song, album_id, album)


class PrepareAlbumFromSongBody(BaseModel):
    song_id: int
    album_id: Optional[int] = None
    title: Optional[str] = None


@router.post("/prepare-from-song")
async def prepare_album_from_song(
    body: PrepareAlbumFromSongBody,
    library: LibraryService = Depends(_get_library),
) -> dict:
    """
    Returns the add/update payload to create (if album_id is null) and sync an album from a song.
    Does not write — caller sends result to /mutate.
    """
    song = library.get_song(body.song_id)
    if not song:
        raise HTTPException(status_code=404, detail=f"Song {body.song_id} not found")

    if body.album_id:
        album = library.get_album(body.album_id)
        if not album:
            raise HTTPException(
                status_code=404, detail=f"Album {body.album_id} not found"
            )
        return _sync_diff(song, body.album_id, album)

    # No album yet — return only the album creation item.
    # Credits/publishers are synced in a follow-up syncAlbumFromSong call once the album ID is known.
    album_title = (body.title or song.media_name or "Unknown Album").strip()
    add = [
        {
            "type": "album",
            "song_id": body.song_id,
            "id": None,
            "name": album_title,
            "album_type": ALBUM_DEFAULT_TYPE,
            "release_year": song.year,
            "track_number": 1,
            "disc_number": 1,
        }
    ]

    return {"add": add}
