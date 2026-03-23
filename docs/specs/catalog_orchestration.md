# Spec: Catalog Orchestration (Atomic Ingestion & Deletion)

## 1. CatalogService.ingest_file(file_path: str) -> Song
**Responsibility**: The high-level orchestrator for adding a new file to the library.

### Workflow:
1. **Extraction**: Calls `MetadataService.extract_metadata` to get raw tags (including the virtual `TLEN`).
2. **Parsing**: Calls `MetadataParser.parse` to convert raw tags into a `Song` domain model.
3. **Hashing**: Calculates `audio_hash` (handled via `calculate_audio_hash` utility).
4. **Validation**: Double-checks for collisions (Path/Hash) via `MediaSourceRepository`.
5. **Persistence**:
    - Starts a database transaction.
    - Calls `SongRepository.insert(song, conn)`.
    - (Future) Logs the `IMPORT` action in `AuditService`.
    - Commits transaction.
6. **Hydration**: Returns the full `Song` object via `self.get_song(new_id)`.

---

## 2. CatalogService.delete_song(song_id: int) -> bool
**Responsibility**: Atomic hard delete of a song and all its relations.

### Workflow:
1. **Verification**: Checks if the song exists via `SongRepository.get_by_id`.
2. **Persistence**:
    - Starts a database transaction.
    - (Future) Snapshots the record for `AuditService.log_delete`.
    - Calls `MediaSourceRepository.delete(song_id, conn)`.
    - Commits transaction.
3. **Result**: Returns `True` if successful.

---

## 3. Method Signatures

### CatalogService
```python
def ingest_file(self, file_path: str) -> Song: ...
def delete_song(self, song_id: int) -> bool: ...
```

### Repositories
- `MediaSourceRepository.delete(source_id: int, conn: sqlite3.Connection) -> bool` (Already implemented)
- `SongRepository.insert(song: Song, conn: sqlite3.Connection) -> int` (Already implemented)

---

## 4. Test Strategy
- **test_ingest_file_success**: Verify a new file creates records in `MediaSources` and `Songs`.
- **test_ingest_file_collision**: Verify it raises an error (or returns status) if path/hash exists.
- **test_delete_song_success**: Verify record is gone from both tables.
