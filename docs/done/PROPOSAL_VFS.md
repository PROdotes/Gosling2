# PROPOSAL: Virtual File System (VFS) for ZIP Handling

## Objective
Establish a centralized, architectural layer to handle "Virtual Paths" (e.g., `archive.zip|member.mp3`). This prevents spreading ZIP-specific logic throughout the codebase and ensures secondary services (Metadata, Hashing, Playback) remain agnostic of the underlying storage medium.

## Core Component: `VFS` (`src/core/vfs.py`)

The `VFS` class will be a static utility or singleton providing:

1.  **Path Resolution**:
    - `is_virtual(path: str) -> bool`: Checks for the virtual separator (`|`).
    - `split_path(path: str) -> Tuple[str, str]`: Splits into `(archive_path, member_path)`.

2.  **Data Retrieval**:
    - `read_bytes(path: str) -> bytes`:
        - If physical: Standard file read.
        - If virtual: Open ZIP, read member bytes.
    - `get_stream(path: str) -> io.BytesIO`: Returns a file-like object for Mutagen/FFmpeg.

3.  **Metadata Cache (Optional)**:
    - To avoid repeated ZIP opens, the VFS can cache the `namelist` or basic file stats of recently accessed archives.

## Integration Plan

### 1. Database & Staging
- Import Service will support a "Staged" or "Virtual" index mode.
- Path in DB: `C:/Music/Album.zip|01. Song.mp3`
- `Song` model remains unchanged (it just stores the string).

### 2. Metadata & Hashing (Refactor)
- **MetadataService**: Instead of passing `path` string into `MP3(path)`, it will call `VFS.read_bytes(path)` or `VFS.get_stream(path)`.
- **AudioHash**: Similarly, calls `VFS.read_bytes(path)` to get the data chunk.
- **Benefits**: No more `if "|" in path` logic in these files.

### 3. Playback
- `PlaybackService` will use `VFS` to extract the member to a temporary file (or buffer if supported by the engine) before playback.

### 4. Realization ("Explode")
- A new command in the Library: `Realize Staged Files`.
- Logic: Extract members from ZIP, move to Library folders, update DB path to physical location.

## Success Criteria
- [ ] `audio_hash.py` has ZERO mention of `zipfile`.
- [ ] `MetadataService` has ZERO mention of `zipfile`.
- [ ] User can "Import" a ZIP instantly (metadata only).
- [ ] User can play songs directly from an un-extracted ZIP.
