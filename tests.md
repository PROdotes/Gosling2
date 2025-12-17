# Test Suite Documentation

## 🔍 Focus: TempoBPM Usage
The following tests explicitly reference the `TempoBPM` field or column. These are critical for verifying changes related to this field.

- `tests/unit/test_criteria_sync.py`
- `tests/unit/data/test_schema_model_cross_ref.py`
- `tests/unit/data/test_database_schema.py`
- `tests/unit/data/repositories/test_song_persistence_integrity.py`
- `tests/unit/data/repositories/test_song_repository_schema.py`
- `tests/unit/data/repositories/test_song_repository_get_path.py`
- `tests/unit/data/repositories/test_song_object_mapping.py`
- `tests/simulation_genre_addition.py`

---

## Full Test Suite

### Integration Tests
- `tests/integration/test_main_window_integration.py`

### Unit Tests

#### Root Tests
- `tests/unit/test_criteria_sync.py` (Also in Focus group)

#### Business Layer
- `tests/unit/business/services/test_library_service.py`
- `tests/unit/business/services/test_library_service_schema.py`
- `tests/unit/business/services/test_metadata_service.py`
- `tests/unit/business/services/test_metadata_service_comprehensive.py`
- `tests/unit/business/services/test_metadata_service_coverage.py`
- `tests/unit/business/services/test_metadata_service_mutation.py`
- `tests/unit/business/services/test_playback_crossfade.py`
- `tests/unit/business/services/test_playback_service.py`
- `tests/unit/business/services/test_playback_service_cleanup.py`
- `tests/unit/business/services/test_playback_service_mutation.py`
- `tests/unit/business/services/test_settings_manager.py`

#### Data Layer
**Models**
- `tests/unit/data/models/test_contributor_model.py`
- `tests/unit/data/models/test_role_model.py`
- `tests/unit/data/models/test_song_integrity.py`
- `tests/unit/data/models/test_song_model.py`

**Repositories**
- `tests/unit/data/repositories/test_base_repository.py`
- `tests/unit/data/repositories/test_contributor_repository.py`
- `tests/unit/data/repositories/test_contributor_repository_schema.py`
- `tests/unit/data/repositories/test_duplicate_reproduction.py`
- `tests/unit/data/repositories/test_security_injection.py`
- `tests/unit/data/repositories/test_song_object_mapping.py` (Also in Focus group)
- `tests/unit/data/repositories/test_song_persistence_integrity.py` (Also in Focus group)
- `tests/unit/data/repositories/test_song_repository.py`
- `tests/unit/data/repositories/test_song_repository_exceptions.py`
- `tests/unit/data/repositories/test_song_repository_extra.py`
- `tests/unit/data/repositories/test_song_repository_get_path.py` (Also in Focus group)
- `tests/unit/data/repositories/test_song_repository_mutation.py`
- `tests/unit/data/repositories/test_song_repository_schema.py` (Also in Focus group)

**Other Data Tests**
- `tests/unit/data/test_database_config.py`
- `tests/unit/data/test_database_schema.py` (Also in Focus group)
- `tests/unit/data/test_schema_model_cross_ref.py` (Also in Focus group)

#### Presentation Layer
**Views**
- `tests/unit/presentation/views/test_main_window.py`
- `tests/unit/presentation/views/test_main_window_cleanup.py`
- `tests/unit/presentation/views/test_mainwindow_edge_cases.py`

**Widgets**
- `tests/unit/presentation/widgets/test_filter_widget.py`
- `tests/unit/presentation/widgets/test_filter_widget_integrity.py`
- `tests/unit/presentation/widgets/test_library_widget.py`
- `tests/unit/presentation/widgets/test_library_context_menu.py`
- `tests/unit/presentation/widgets/test_library_widget_constants.py`
- `tests/unit/presentation/widgets/test_library_widget_drag_drop.py`
- `tests/unit/presentation/widgets/test_library_widget_filtering.py`
- `tests/unit/presentation/widgets/test_playback_control_widget.py`
- `tests/unit/presentation/widgets/test_playback_control_widget_mutation.py`
- `tests/unit/presentation/widgets/test_playlist_widget.py`
- `tests/unit/presentation/widgets/test_playlist_widget_extra.py`
- `tests/unit/presentation/widgets/test_seek_slider.py`
