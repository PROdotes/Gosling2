import os
import shutil
from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.encoders import jsonable_encoder
import json
import asyncio

from src.models.view_models import (
    SongView,
    FolderScanRequest,
    IngestionReportView,
    CleanupOriginalRequest,
    IngestStatusModel,
)
from src.services.catalog_service import CatalogService
from src.services.converter import convert_to_mp3
from src.services.logger import logger
from src.engine.config import (
    STAGING_DIR,
    ACCEPTED_EXTENSIONS,
    WAV_AUTO_CONVERT,
    get_downloads_folder,
    ProcessingStatus,
    PARSER_PRESETS_PATH,
)
from src.utils.audio_hash import calculate_audio_hash

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


def _get_service() -> CatalogService:
    return CatalogService()


async def _stream_ingestion(service, work_items):
    """
    Shared streaming ingestion pipeline.
    work_items: [(staged_path, original_path), ...]
    Yields NDJSON with session status and per-file results.
    """

    task_id = str(uuid4())
    service._ingestion_service.register_task(task_id, len(work_items))

    try:
        yield f"{json.dumps(jsonable_encoder(service._ingestion_service.get_session_status()))}\n"
        await asyncio.sleep(0)

        for staged_path, original_path in work_items:
            if Path(staged_path).suffix.lower() == ".wav":
                if WAV_AUTO_CONVERT:
                    try:
                        mp3 = await run_in_threadpool(convert_to_mp3, Path(staged_path))
                        res = await run_in_threadpool(
                            service._ingestion_service._ingest_single,
                            str(mp3),
                            original_path=original_path,
                        )
                    except RuntimeError as e:
                        res = {"status": "ERROR", "message": str(e)}
                else:
                    res = await run_in_threadpool(
                        service.ingest_wav_as_converting,
                        staged_path,
                        original_path=original_path,
                    )
                    if res["status"] == "CONVERTING":
                        res["status"] = "PENDING_CONVERT"
                    if res.get("song"):
                        res["song"] = SongView.from_domain(res["song"])
                    res["staged_path"] = staged_path
            else:
                res = await run_in_threadpool(
                    service._ingestion_service._ingest_single,
                    staged_path,
                    original_path=original_path,
                )
                if res.get("song"):
                    res["song"] = SongView.from_domain(res["song"])

            service._ingestion_service._update_task(task_id, res["status"])
            status = service._ingestion_service.get_session_status()
            yield f"{json.dumps(jsonable_encoder({**status, 'last_result': res}))}\n"
            await asyncio.sleep(0)

    except Exception as e:
        logger.error(f"[IngestRouter] Stream error: {e}")
        yield f"{json.dumps({'error': str(e)})}\n"


@router.get("/parser-config")
async def get_parser_config():
    """Retrieve dynamic tokens and presets for the Filename Parser."""
    if not PARSER_PRESETS_PATH.exists():
        return {"tokens": [], "presets": []}
    with open(PARSER_PRESETS_PATH, "r") as f:
        return json.load(f)


@router.get("/downloads-folder")
async def get_downloads_folder_json():
    """Retrieve the platform-specific default downloads folder."""
    return JSONResponse({"path": get_downloads_folder()})


@router.get("/formats")
async def get_accepted_formats():
    """Retrieve the list of supported file extensions for ingestion."""
    return JSONResponse({"extensions": ACCEPTED_EXTENSIONS})


@router.get("/status", response_model=IngestStatusModel)
async def get_ingest_status():
    """Returns the 'Whole Model' (pending/success/action) for the active session."""
    service = _get_service()
    status = service._ingestion_service.get_session_status()
    return status


@router.post("/reset-status")
async def reset_ingest_status():
    """Resets the session-wide success/action counters."""
    _get_service()._ingestion_service.reset_session_status()
    return {"status": "RESET"}


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """Upload files via browser and stream ingestion progress."""
    logger.info(f"[IngestRouter] -> upload_files(count={len(files)})")

    os.makedirs(STAGING_DIR, exist_ok=True)
    work_items = []

    for file in files:
        if not file.filename:
            continue
        safe_filename = Path(file.filename.replace("\\", "/")).name
        if Path(safe_filename).suffix.lower() not in ACCEPTED_EXTENSIONS:
            continue
        staged_path = os.path.join(STAGING_DIR, f"{uuid4()}_{safe_filename}")
        try:
            with open(staged_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            original_src = os.path.join(get_downloads_folder(), safe_filename)
            work_items.append((staged_path, original_src))
        except Exception as e:
            logger.error(f"[IngestRouter] Failed to stage {file.filename}: {e}")

    if not work_items:
        raise HTTPException(status_code=400, detail="No valid audio files found.")

    service = _get_service()
    return StreamingResponse(
        _stream_ingestion(service, work_items),
        media_type="application/x-ndjson",
    )


@router.get("/cleanup-origin/{song_id}")
async def get_cleanup_origin(song_id: int):
    """Checks if there is a known original file path for this song."""
    service = _get_service()
    path = service.get_staging_origin(song_id)
    return {"id": song_id, "origin_path": path, "exists": bool(path)}


@router.post("/convert-wav")
async def convert_wav(staged_path: str) -> dict:
    """Convert a staged WAV to MP3. Called when user confirms a PENDING_CONVERT card.
    The WAV was already ingested with status=3; this converts it and finalizes the DB record.
    """
    logger.info(f"[IngestRouter] -> convert_wav(staged_path='{staged_path}')")
    service = _get_service()
    try:
        existing = service._song_repo.get_by_path(staged_path)
        if existing is None:
            logger.error(
                f"[IngestRouter] convert_wav: no DB record for '{staged_path}'"
            )
            return {
                "status": "ERROR",
                "message": "No DB record found for this WAV. Try re-uploading.",
            }
        mp3 = convert_to_mp3(Path(staged_path))
        surviving_id = service.finalize_wav_conversion(existing.id, str(mp3))
        hydrated = service.get_song(surviving_id)
        status = "INGESTED" if surviving_id == existing.id else "ALREADY_EXISTS"
        result = {"status": status}
        if hydrated:
            result["song"] = SongView.from_domain(hydrated)
        return result
    except RuntimeError as e:
        logger.error(f"[IngestRouter] convert_wav failed: {e}")
        return {"status": "ERROR", "message": str(e)}


@router.post("/resolve-conflict")
async def resolve_conflict(ghost_id: int, staged_path: str) -> IngestionReportView:
    """
    Resolve a ghost conflict by reactivating the soft-deleted record with new metadata.

    Takes the ghost record ID and the path to the staged file,
    updates the ghost record with new metadata, and sets IsDeleted=0.

    Example:
        POST /api/v1/ingest/resolve-conflict?ghost_id=123&staged_path=/path/to/staged/file.mp3
    """
    logger.info(
        f"[IngestRouter] -> resolve_conflict(ghost_id={ghost_id}, staged_path='{staged_path}')"
    )

    try:
        service = _get_service()
        # Heuristic for the original path of an uploaded staged file
        original_src = os.path.join(
            get_downloads_folder(), Path(staged_path).name.split("_", 1)[-1]
        )
        result = service.resolve_conflict(
            ghost_id, staged_path, original_path=original_src
        )

        # Convert Domain Song to SongView if present
        if "song" in result and result["song"]:
            result["song"] = SongView.from_domain(result["song"])

        return IngestionReportView(**result)

    except Exception as e:
        logger.error(f"[IngestRouter] Conflict resolution error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Conflict resolution failed: {str(e)}"
        )


@router.post("/scan-folder")
async def scan_folder(request: FolderScanRequest):
    """
    Server-side folder scanning and ingestion.
    Streams ingestion progress via NDJSON.
    """
    logger.info(
        f"[IngestRouter] -> scan_folder(path='{request.folder_path}', recursive={request.recursive})"
    )

    service = _get_service()
    audio_files = service.scan_folder(request.folder_path, request.recursive)

    if not audio_files:
        raise HTTPException(
            status_code=404,
            detail=f"No audio files found in {request.folder_path}. Accepted extensions: {ACCEPTED_EXTENSIONS}",
        )

    os.makedirs(STAGING_DIR, exist_ok=True)

    work_items = []
    if request.in_place:
        for file_path in audio_files:
            work_items.append((file_path, None))
        logger.info(f"[IngestRouter] In-place processing {len(work_items)} files.")
    else:
        for file_path in audio_files:
            try:
                uuid_filename = f"{uuid4()}_{Path(file_path).name}"
                staged_path = os.path.join(STAGING_DIR, uuid_filename)
                shutil.copy2(file_path, staged_path)
                work_items.append((staged_path, file_path))
                logger.debug(f"[IngestRouter] Staged: {file_path} -> {staged_path}")
            except Exception as e:
                logger.error(f"[IngestRouter] Failed to stage {file_path}: {e}")

    if not work_items:
        raise HTTPException(
            status_code=500, detail="Failed to stage any files for ingestion"
        )

    logger.info(
        f"[IngestRouter] <- scan_folder() queuing {len(work_items)} files for ingestion"
    )
    return StreamingResponse(
        _stream_ingestion(service, work_items),
        media_type="application/x-ndjson",
    )


@router.delete("/songs/{song_id:int}")
async def delete_song(song_id: int):
    """
    Atomic hard-delete of a song by ID.
    Triggers DB cascade and physical cleanup if in staging.
    """
    logger.info(f"[IngestRouter] -> delete_song(id={song_id})")
    service = _get_service()
    success = service.delete_song(song_id)

    if not success:
        logger.warning(f"[IngestRouter] Delete failed: Song ID {song_id} not found.")
        raise HTTPException(status_code=404, detail=f"Song ID {song_id} not found.")

    logger.info(f"[IngestRouter] <- delete_song(id={song_id}) SUCCESS")
    return {"status": "DELETED", "id": song_id}


@router.post("/cleanup-original")
async def cleanup_original_file(request: CleanupOriginalRequest):
    """
    Physical deletion of the original source file (e.g. from Downloads).
    Safety: Path must be within the user's Downloads folder.
    """
    downloads = get_downloads_folder()
    if not downloads:
        raise HTTPException(
            status_code=500, detail="Downloads folder not identified on this platform."
        )

    try:
        service = _get_service()
        file_path = request.file_path

        if request.song_id is not None:
            # Enhanced cleanup via song_id lookup
            success = service.delete_original_source(request.song_id)
            if success:
                return {"status": "DELETED", "id": request.song_id}
            else:
                # If we have song_id but lookup fails or file is already gone
                origin = service.get_staging_origin(request.song_id)
                if not origin:
                    raise HTTPException(
                        status_code=404,
                        detail="No original source link found for this song.",
                    )
                file_path = origin

        if not file_path:
            raise HTTPException(
                status_code=400, detail="Either file_path or song_id must be provided."
            )

        # Legacy direct path cleanup (still used by some UI parts)
        # Security: Ensure the path is within the Downloads folder
        real_downloads = Path(downloads).resolve()
        real_target = Path(file_path).resolve()

        if not real_target.is_relative_to(real_downloads):
            logger.warning(
                f"[IngestRouter] Security: Blocked deletion of file outside Downloads: {file_path}"
            )
            raise HTTPException(
                status_code=403,
                detail="Deletion is restricted to the Downloads folder for safety.",
            )

        if not os.path.exists(real_target):
            # If path existed in DB but is gone from disk, clear it
            if request.song_id:
                service._edit_service._staging_repo.clear_origin(request.song_id)
            return {"status": "ALREADY_GONE", "path": str(real_target)}

        os.remove(real_target)
        if request.song_id:
            service._edit_service._staging_repo.clear_origin(request.song_id)

        logger.info(f"[IngestRouter] <- cleanup_original_file() SUCCESS: {real_target}")
        return {"status": "DELETED", "path": str(real_target)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[IngestRouter] Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/pending-convert")
async def get_pending_convert():
    """List songs with processing_status=3 (WAV staged, awaiting conversion)."""
    service = _get_service()
    songs = service._song_repo.get_by_processing_status(ProcessingStatus.CONVERTING)
    results = []
    for s in songs:
        hydrated = service.get_song(s.id)
        if hydrated:
            results.append(
                {
                    "status": "PENDING_CONVERT",
                    "staged_path": s.source_path,
                    "song": SongView.from_domain(hydrated).model_dump(),
                }
            )
    return JSONResponse(results)


@router.get("/staging-orphans")
async def get_staging_orphans():
    """
    List files in the staging folder that have no matching DB record.
    Returns [{filename, path, size_bytes}].
    """
    if not os.path.exists(STAGING_DIR):
        return JSONResponse([])

    service = _get_service()
    orphans = []
    for fname in os.listdir(STAGING_DIR):
        fpath = os.path.join(STAGING_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        # Ghost check: Hash discovery (No new methods, reusing MediaSourceRepository logic)
        audio_hash = calculate_audio_hash(fpath)
        existing = service._song_repo.get_source_metadata_by_hash(audio_hash)

        # Orphan if: no DB record, soft-deleted ghost, or DB record points elsewhere (leftover conflict file)
        is_leftover = (
            existing
            and not existing["is_deleted"]
            and os.path.normpath(existing["source_path"]) != os.path.normpath(fpath)
        )
        if not existing or existing["is_deleted"] or is_leftover:
            orphans.append(
                {
                    "filename": fname,
                    "path": fpath,
                    "size_bytes": os.path.getsize(fpath),
                    "is_ghost": bool(existing and existing["is_deleted"]),
                    "ghost_id": existing["id"] if existing else None,
                }
            )

    return JSONResponse(orphans)


@router.delete("/staging-orphans")
async def delete_staging_orphan(path: str):
    """
    Delete a specific file from staging, only if it has no DB record.
    Safety: Path must be within STAGING_DIR.
    """
    real_staging = Path(STAGING_DIR).resolve()
    real_target = Path(path).resolve()

    if not real_target.is_relative_to(real_staging):
        raise HTTPException(
            status_code=403, detail="Path must be within the staging folder."
        )

    if not os.path.isfile(real_target):
        raise HTTPException(status_code=404, detail="File not found.")

    service = _get_service()
    song = service._song_repo.get_by_path(str(real_target))
    if song is not None:
        raise HTTPException(
            status_code=409,
            detail="File is linked to a DB record. Delete the song instead.",
        )

    try:
        os.remove(real_target)
        logger.info(f"[IngestRouter] Deleted staging orphan: {real_target}")
        return {"status": "DELETED", "path": real_target}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
