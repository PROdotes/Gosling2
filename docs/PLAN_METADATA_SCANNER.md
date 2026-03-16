# Plan: Phase 2.1.1 - Metadata Scanner (JSON-Driven & No Mocks)

## Objective
Implement a high-fidelity metadata extraction service that dynamically maps ID3 frames to internal fields using a configuration file, ensuring 100% test coverage with 0 mocks.

## 1. Lookup Alignment
Update `docs/lookup/services.md` to reflect the dynamic mapping capability.

## 2. Technical Decisions
- **Tool**: `mutagen`.
- **Dynamic Config**: Load `tests/fixtures/id3_frames.json` (or a production equivalent if applicable) to map frames to fields.
- **Strict Testing**: 
    - **No Mocks**: Replace `unittest.mock` usage in `test_metadata_service.py` with physical files.
    - **Edge Cases**: Corrupt files (truncated buffers), files with missing headers, and files with only v2.3 or v2.4 tags.

## 3. Implementation Steps
### Service Layer
1. **Refactor**: Modify `MetadataService` to load the frame mapping from a JSON file.
2. **Logic**: Iterate through tags in the audio file and map them back to domain fields (title, artist, etc.) based on the configuration.
3. **Resilience**: Maintain fallback to `EasyID3` if standard frame access fails.

### Testing (PURGE MOCKS)
1. **Remove**: Delete `test_metadata_service_elusive_lines` from `tests/test_metadata_service.py`.
2. **Implement**: 
    - Generate a "truly invalid" file (e.g. `b"ID3\xff\xff\xff"`) to trigger `mutagen` parsing errors.
    - Test `tags is None` by using a file with no ID3 header at all.
    - Verification: Ensure `pytest --cov` remains at 100% without mocks.

## 4. 1:1:1 Agreement
- **Method**: `MetadataService.extract_metadata(path: str)`
- **Location**: `src/services/metadata_service.py`
- **Verification**: `pytest tests/test_metadata_service.py`

