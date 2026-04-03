import os
import shutil
from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from src.models.view_models import (
    SongView,
    FolderScanRequest,
    BatchIngestReport,
    IngestionReportView,
    CleanupOriginalRequest,
)
from src.services.catalog_service import CatalogService
from src.services.converter import convert_to_mp3
from src.services.logger import logger
from src.engine.config import (
    get_db_path,
    STAGING_DIR,
    ACCEPTED_EXTENSIONS,
    WAV_AUTO_CONVERT,
    get_downloads_folder,
)

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


def _get_service() -> CatalogService:
    """Service factory for the ingestion router."""
    return CatalogService(get_db_path())




@router.get("/downloads-folder")
async def get_downloads_folder_json():
    """Retrieve the platform-specific default downloads folder."""
    return JSONResponse({"path": get_downloads_folder()})


@router.get("/formats")
async def get_accepted_formats():
    """Retrieve the list of supported file extensions for ingestion."""
    return JSONResponse({"extensions": ACCEPTED_EXTENSIONS})


@router.post("/upload", response_model=BatchIngestReport)
async def upload_files(files: list[UploadFile] = File(...)) -> BatchIngestReport:
    """
    Physical file ingestion entry point (supports batch uploads).
    Browser automatically flattens folders into individual files.

    1. Validate extensions
    2. Save all files to STAGING_DIR with UUID filenames
    3. Orchestrate batch ingestion via CatalogService
    4. Return BatchIngestReport with aggregate stats and per-file results.
    """
    logger.info(f"[IngestRouter] -> upload_files(count={len(files)})")

    # 1. Ensure staging exists
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR, exist_ok=True)

    # 2. Stage all valid files
    staged_paths = []
    for file in files:
        # Validate filename
        if not file.filename:
            logger.warning("[IngestRouter] Skipping file with no filename")
            continue

        # Validate extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ACCEPTED_EXTENSIONS:
            logger.warning(
                f"[IngestRouter] Skipping file with invalid extension '{file_ext}': {file.filename}"
            )
            continue

        # Save to staging with UUID filename to prevent collisions
        uuid_filename = f"{uuid4()}_{file.filename}"
        staged_path = os.path.join(STAGING_DIR, uuid_filename)

        try:
            with open(staged_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            staged_paths.append(staged_path)
            logger.debug(f"[IngestRouter] Staged: {file.filename} -> {staged_path}")
        except Exception as e:
            logger.error(f"[IngestRouter] Failed to stage {file.filename}: {e}")
            # Continue with other files instead of failing the entire batch

    if not staged_paths:
        raise HTTPException(
            status_code=400,
            detail=f"No valid audio files found. Accepted extensions: {ACCEPTED_EXTENSIONS}",
        )

    # 3. Split WAVs from non-WAVs
    wav_paths = [p for p in staged_paths if Path(p).suffix.lower() == ".wav"]
    ingest_paths = [p for p in staged_paths if Path(p).suffix.lower() != ".wav"]

    service = _get_service()
    wav_results = []

    if wav_paths:
        if WAV_AUTO_CONVERT:
            # Synchronous conversion: convert then ingest normally
            for wav in wav_paths:
                try:
                    mp3 = convert_to_mp3(Path(wav))
                    ingest_paths.append(str(mp3))
                except RuntimeError as e:
                    logger.error(f"[IngestRouter] WAV conversion failed for {wav}: {e}")
        else:
            # Prompt mode: return PENDING_CONVERT cards, user confirms conversion manually
            for wav in wav_paths:
                wav_results.append({"status": "PENDING_CONVERT", "staged_path": wav})

    # 4. Batch ingest non-WAVs
    if not ingest_paths and not wav_results:
        raise HTTPException(
            status_code=400,
            detail=f"No valid audio files found. Accepted extensions: {ACCEPTED_EXTENSIONS}",
        )

    try:
        combined_results = list(wav_results)
        if ingest_paths:
            batch_report = service.ingest_batch(ingest_paths)
            for result in batch_report["results"]:
                if "song" in result and result["song"]:
                    result["song"] = SongView.from_domain(result["song"])
            combined_results.extend(batch_report["results"])

        total = len(combined_results)
        ingested = sum(1 for r in combined_results if r.get("status") in ("INGESTED", "CONVERTING"))
        duplicates = sum(1 for r in combined_results if r.get("status") in ("ALREADY_EXISTS", "MATCHED_HASH"))
        errors = sum(1 for r in combined_results if r.get("status") == "ERROR")

        return BatchIngestReport(
            total_files=total,
            ingested=ingested,
            duplicates=duplicates,
            errors=errors,
            results=combined_results,
        )

    except Exception as e:
        logger.error(f"[IngestRouter] Batch ingestion error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal Ingestion Error: {str(e)}"
        )


def _run_wav_conversions(wav_paths: list[str], service: CatalogService) -> None:
    """
    Background task: convert each staged WAV to MP3 and finalize the DB record.
    Each WAV was already ingested with processing_status=3; this moves it to status=1.
    """
    for wav in wav_paths:
        song_id = None
        try:
            # Look up the song_id by path before conversion deletes the WAV
            existing = service._song_repo.get_by_path(wav)
            if existing:
                song_id = existing.id
            mp3 = convert_to_mp3(Path(wav))
            if song_id is not None:
                service.finalize_wav_conversion(song_id, str(mp3))
            else:
                logger.warning(f"[IngestRouter] No DB record found for {wav}, skipping finalize")
        except RuntimeError as e:
            logger.error(f"[IngestRouter] Background conversion failed for {wav}: {e}")


@router.post("/convert-wav")
async def convert_wav(staged_path: str) -> dict:
    """Convert a staged WAV to MP3 and ingest. Called when user confirms a PENDING_CONVERT card."""
    logger.info(f"[IngestRouter] -> convert_wav(staged_path='{staged_path}')")
    service = _get_service()
    try:
        mp3 = convert_to_mp3(Path(staged_path))
        result = service.ingest_file(str(mp3))
        if result.get("song"):
            result["song"] = SongView.from_domain(result["song"])
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
        result = service.resolve_conflict(ghost_id, staged_path)

        # Convert Domain Song to SongView if present
        if "song" in result and result["song"]:
            result["song"] = SongView.from_domain(result["song"])

        return IngestionReportView(**result)

    except Exception as e:
        logger.error(f"[IngestRouter] Conflict resolution error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Conflict resolution failed: {str(e)}"
        )


@router.post("/scan-folder", response_model=BatchIngestReport)
async def scan_folder(request: FolderScanRequest) -> BatchIngestReport:
    """
    Server-side folder scanning and ingestion.
    Scans a local filesystem path for audio files and ingests them.

    Use this for desktop app or when files are already on the server.
    For browser uploads, use /upload instead.

    Example:
        POST /api/v1/ingest/scan-folder
        {
            "folder_path": "Z:\\Songs\\New Album",
            "recursive": true
        }
    """
    logger.info(
        f"[IngestRouter] -> scan_folder(path='{request.folder_path}', recursive={request.recursive})"
    )

    # 1. Scan for audio files
    service = _get_service()
    audio_files = service.scan_folder(request.folder_path, request.recursive)

    if not audio_files:
        raise HTTPException(
            status_code=404,
            detail=f"No audio files found in {request.folder_path}. Accepted extensions: {ACCEPTED_EXTENSIONS}",
        )

    # 2. Ensure staging exists
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR, exist_ok=True)

    # 3. Copy files to staging
    staged_paths = []
    for file_path in audio_files:
        try:
            uuid_filename = f"{uuid4()}_{Path(file_path).name}"
            staged_path = os.path.join(STAGING_DIR, uuid_filename)
            shutil.copy2(file_path, staged_path)
            staged_paths.append(staged_path)
            logger.debug(f"[IngestRouter] Staged: {file_path} -> {staged_path}")
        except Exception as e:
            logger.error(f"[IngestRouter] Failed to stage {file_path}: {e}")
            # Continue with other files

    if not staged_paths:
        raise HTTPException(
            status_code=500, detail="Failed to stage any files for ingestion"
        )

    # 4. Batch ingest
    try:
        batch_report = service.ingest_batch(staged_paths)

        # 5. Convert Domain Songs to SongViews
        for result in batch_report["results"]:
            if "song" in result and result["song"]:
                result["song"] = SongView.from_domain(result["song"])

        logger.info(
            f"[IngestRouter] <- scan_folder() "
            f"found={len(audio_files)} ingested={batch_report['ingested']}"
        )
        return BatchIngestReport(**batch_report)

    except Exception as e:
        logger.error(f"[IngestRouter] Folder scan ingestion error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Internal Ingestion Error: {str(e)}"
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
    logger.info(f"[IngestRouter] -> cleanup_original_file(path='{request.file_path}')")

    downloads = get_downloads_folder()
    if not downloads:
        raise HTTPException(
            status_code=500, detail="Downloads folder not identified on this platform."
        )

    # Security: Ensure the path starts with the Downloads folder
    # Need realpath to prevent '..' traversal or tricky symlinks
    real_downloads = os.path.realpath(downloads)
    real_target = os.path.realpath(request.file_path)

    if not real_target.startswith(real_downloads):
        logger.warning(
            f"[IngestRouter] Security: Blocked deletion of file outside Downloads: {request.file_path}"
        )
        raise HTTPException(
            status_code=403,
            detail="Deletion is restricted to the Downloads folder for safety.",
        )

    if not os.path.exists(real_target):
        logger.warning(f"[IngestRouter] File not found for cleanup: {request.file_path}")
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        os.remove(real_target)
        logger.info(f"[IngestRouter] <- cleanup_original_file() SUCCESS: {real_target}")
        return {"status": "DELETED", "path": real_target}
    except Exception as e:
        logger.error(f"[IngestRouter] Cleanup failed for {real_target}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
