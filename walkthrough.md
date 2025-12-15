# Incomplete Song Filter Walkthrough

## Completed Tasks
- [x] Create `src/completeness_criteria.json` with initial validation rules.
- [x] Create `tests/unit/test_criteria_sync.py` to ensure JSON rules match Database Schema.
- [x] Modify `LibraryWidget` to:
    - Load validation rules.
    - Add "Show Incomplete Only" checkbox.
    - Filter table rows based on rules.
    - **Highlight specific cells** that violate the criteria (light red) when the filter is active.
    - **Dynamic Column Visibility**: When filter is ON, show only columns relevant to the criteria (Required). When OFF, revert to user's saved visibility settings.

## Crossfade Controls Update
- **Refactoring**: Replaced the "Crossfade" checkbox with a **Dropdown Menu**.
- **Options**: Select from `0s (Off)`, `1s`, `2s`, `3s`, `4s`, `5s`, `10s`.
- **Behavior**: Selecting `0s` disables crossfade. Any other value enables it with the specified duration.

### Bug Fix: Skip Button State
- Fixed an issue where selecting `0s (Off)` would disabling the Skip button.
- The button now correctly remains enabled (provided there are next songs in the playlist) regardless of the crossfade setting.

## Verification Results

### Automated Tests
- `tests/unit/test_criteria_sync.py` passed.
- `tests/unit/presentation/widgets/test_library_widget_filtering.py` passed.
- `tests/unit/presentation/widgets/test_playback_control_widget.py` updated to cover dropdown logic.

### Feature Behavior
- **Incomplete Filter**: (As described above).
- **Playback Control**: Crossfade settings are now explicit and easier to discover via the dropdown.

## Usage
1. Open the application.
2. In the Library view, click the "Show Incomplete Only" checkbox.
3. The table adjusts to show only incomplete songs and relevant columns.
4. **Playback**: Use the new dropdown in the bottom control bar to set crossfade duration or turn it off.
