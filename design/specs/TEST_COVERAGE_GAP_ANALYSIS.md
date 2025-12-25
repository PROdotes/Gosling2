# 🧪 Test Coverage Gap Analysis
This inventory maps every function in `src/` to its code coverage status.

| File | Function | Coverage | Status |
| :--- | :--- | :--- | :--- |
| `src\business\services\duplicate_scanner.py` | `DuplicateScannerService.check_isrc_duplicate` | 85% | ⚠️ |
| `src\business\services\duplicate_scanner.py` | `DuplicateScannerService.check_audio_duplicate` | 100% | ✅ |
| `src\business\services\library_service.py` | `LibraryService.add_file` | 100% | ✅ |
| `src\business\services\library_service.py` | `LibraryService.get_all_songs` | 100% | ✅ |
| `src\business\services\library_service.py` | `LibraryService.delete_song` | 100% | ✅ |
| `src\business\services\library_service.py` | `LibraryService.update_song` | 100% | ✅ |
| `src\business\services\library_service.py` | `LibraryService.update_song_status` | 50% | ⚠️ |
| `src\business\services\library_service.py` | `LibraryService.get_contributors_by_role` | 100% | ✅ |
| `src\business\services\library_service.py` | `LibraryService.get_songs_by_performer` | 100% | ✅ |
| `src\business\services\library_service.py` | `LibraryService.get_songs_by_unified_artist` | 33% | 🔴 |
| `src\business\services\library_service.py` | `LibraryService.get_songs_by_composer` | 50% | ⚠️ |
| `src\business\services\library_service.py` | `LibraryService.get_song_by_path` | 50% | ⚠️ |
| `src\business\services\library_service.py` | `LibraryService.get_song_by_id` | 100% | ✅ |
| `src\business\services\library_service.py` | `LibraryService.find_by_isrc` | 50% | ⚠️ |
| `src\business\services\library_service.py` | `LibraryService.find_by_audio_hash` | 50% | ⚠️ |
| `src\business\services\library_service.py` | `LibraryService.get_all_years` | 50% | ⚠️ |
| `src\business\services\library_service.py` | `LibraryService.get_all_aliases` | 100% | ✅ |
| `src\business\services\library_service.py` | `LibraryService.get_songs_by_year` | 50% | ⚠️ |
| `src\business\services\library_service.py` | `LibraryService.get_songs_by_status` | 50% | ⚠️ |
| `src\business\services\library_service.py` | `LibraryService.get_item_albums` | 50% | ⚠️ |
| `src\business\services\library_service.py` | `LibraryService.assign_album` | 16% | 🔴 |
| `src\business\services\library_service.py` | `LibraryService.get_distinct_filter_values` | 65% | ⚠️ |
| `src\business\services\metadata_service.py` | `MetadataService.extract_from_mp3` | 93% | ✅ |
| `src\business\services\metadata_service.py` | `MetadataService.get_raw_tags` | 6% | 🔴 |
| `src\business\services\metadata_service.py` | `MetadataService.write_tags` | 89% | ⚠️ |
| `src\business\services\metadata_service.py` | `MetadataService.get_values` | 78% | ⚠️ |
| `src\business\services\metadata_service.py` | `MetadataService.clean_list` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService._create_player_pair` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.crossfade_duration` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.crossfade_duration` | 50% | ⚠️ |
| `src\business\services\playback_service.py` | `PlaybackService.crossfade_enabled` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.crossfade_enabled` | 50% | ⚠️ |
| `src\business\services\playback_service.py` | `PlaybackService.active_player` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.active_audio` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService._connect_signals` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService._disconnect_signals` | 10% | 🔴 |
| `src\business\services\playback_service.py` | `PlaybackService._handle_media_status` | 25% | 🔴 |
| `src\business\services\playback_service.py` | `PlaybackService.load` | 33% | 🔴 |
| `src\business\services\playback_service.py` | `PlaybackService.play` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.pause` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.stop` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.seek` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.set_volume` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.get_volume` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService._update_volumes` | 53% | ⚠️ |
| `src\business\services\playback_service.py` | `PlaybackService.get_position` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.get_duration` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.get_state` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.is_playing` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.set_playlist` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.play_at_index` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.crossfade_to` | 9% | 🔴 |
| `src\business\services\playback_service.py` | `PlaybackService.play_next` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService._start_crossfade` | 5% | 🔴 |
| `src\business\services\playback_service.py` | `PlaybackService._on_crossfade_tick` | 12% | 🔴 |
| `src\business\services\playback_service.py` | `PlaybackService._stop_crossfade` | 60% | ⚠️ |
| `src\business\services\playback_service.py` | `PlaybackService.play_previous` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.get_current_index` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.get_playlist` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.cleanup` | 100% | ✅ |
| `src\business\services\playback_service.py` | `PlaybackService.safe_disconnect_all` | 0% | 🔴 |
| `src\business\services\renaming_service.py` | `RenamingService.calculate_target_path` | 85% | ⚠️ |
| `src\business\services\renaming_service.py` | `RenamingService._resolve_routing_rules` | 63% | ⚠️ |
| `src\business\services\renaming_service.py` | `RenamingService.check_conflict` | 100% | ✅ |
| `src\business\services\renaming_service.py` | `RenamingService.rename_song` | 66% | ⚠️ |
| `src\business\services\renaming_service.py` | `RenamingService._sanitize` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_window_geometry` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_window_geometry` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_main_splitter_state` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_main_splitter_state` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_right_panel_tab` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_right_panel_tab` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_default_window_size` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_last_import_directory` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_last_import_directory` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_type_filter` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_type_filter` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_root_directory` | 50% | ⚠️ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_root_directory` | 50% | ⚠️ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_column_layout` | 83% | ⚠️ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_column_layout` | 84% | ⚠️ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_volume` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_volume` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_last_playlist` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_last_playlist` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_last_song_path` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_last_song_path` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_last_position` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_last_position` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_crossfade_enabled` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_crossfade_enabled` | 50% | ⚠️ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_crossfade_duration` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.set_crossfade_duration` | 50% | ⚠️ |
| `src\business\services\settings_manager.py` | `SettingsManager.clear_all` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.sync` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.get_all_keys` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.has_setting` | 100% | ✅ |
| `src\business\services\settings_manager.py` | `SettingsManager.remove_setting` | 100% | ✅ |
| `src\core\logger.py` | `subscribe_to_user_warnings` | 100% | ✅ |
| `src\core\logger.py` | `_setup` | 90% | ✅ |
| `src\core\logger.py` | `get` | 100% | ✅ |
| `src\core\logger.py` | `dev_warning` | 100% | ✅ |
| `src\core\logger.py` | `user_warning` | 100% | ✅ |
| `src\core\logger.py` | `info` | 100% | ✅ |
| `src\core\logger.py` | `debug` | 100% | ✅ |
| `src\core\logger.py` | `error` | 100% | ✅ |
| `src\core\yellberus.py` | `decade_grouper` | 100% | ✅ |
| `src\core\yellberus.py` | `first_letter_grouper` | 75% | ⚠️ |
| `src\core\yellberus.py` | `build_query_select` | 100% | ✅ |
| `src\core\yellberus.py` | `get_field` | 100% | ✅ |
| `src\core\yellberus.py` | `get_visible_fields` | 100% | ✅ |
| `src\core\yellberus.py` | `get_filterable_fields` | 100% | ✅ |
| `src\core\yellberus.py` | `get_required_fields` | 50% | ⚠️ |
| `src\core\yellberus.py` | `validate_row` | 89% | ⚠️ |
| `src\core\yellberus.py` | `yell` | 33% | 🔴 |
| `src\core\yellberus.py` | `validate_schema` | 78% | ⚠️ |
| `src\core\yellberus.py` | `row_to_tagged_tuples` | 92% | ✅ |
| `src\core\yellberus.py` | `check_db_integrity` | 76% | ⚠️ |
| `src\core\yellberus.py` | `cast_from_string` | 4% | 🔴 |
| `src\data\database.py` | `BaseRepository.get_connection` | 100% | ✅ |
| `src\data\database.py` | `BaseRepository._ensure_schema` | 100% | ✅ |
| `src\data\database_config.py` | `DatabaseConfig.get_database_path` | 100% | ✅ |
| `src\data\models\album.py` | `Album.from_row` | 100% | ✅ |
| `src\data\models\publisher.py` | `Publisher.from_row` | 100% | ✅ |
| `src\data\models\song.py` | `Song.from_row` | 82% | ⚠️ |
| `src\data\models\song.py` | `Song.title` | 100% | ✅ |
| `src\data\models\song.py` | `Song.title` | 100% | ✅ |
| `src\data\models\song.py` | `Song.path` | 100% | ✅ |
| `src\data\models\song.py` | `Song.path` | 50% | ⚠️ |
| `src\data\models\song.py` | `Song.file_id` | 100% | ✅ |
| `src\data\models\song.py` | `Song.file_id` | 100% | ✅ |
| `src\data\models\song.py` | `Song.get_display_performers` | 100% | ✅ |
| `src\data\models\song.py` | `Song.get_display_title` | 100% | ✅ |
| `src\data\models\song.py` | `Song.year` | 50% | ⚠️ |
| `src\data\models\song.py` | `Song.year` | 50% | ⚠️ |
| `src\data\models\song.py` | `Song.formatted_duration` | 50% | ⚠️ |
| `src\data\models\song.py` | `Song.get_formatted_duration` | 100% | ✅ |
| `src\data\models\tag.py` | `Tag.from_row` | 100% | ✅ |
| `src\data\repositories\album_repository.py` | `AlbumRepository.get_by_id` | 87% | ⚠️ |
| `src\data\repositories\album_repository.py` | `AlbumRepository.find_by_title` | 100% | ✅ |
| `src\data\repositories\album_repository.py` | `AlbumRepository.find_by_key` | 100% | ✅ |
| `src\data\repositories\album_repository.py` | `AlbumRepository.create` | 100% | ✅ |
| `src\data\repositories\album_repository.py` | `AlbumRepository.get_or_create` | 100% | ✅ |
| `src\data\repositories\album_repository.py` | `AlbumRepository.update` | 63% | ⚠️ |
| `src\data\repositories\album_repository.py` | `AlbumRepository.add_song_to_album` | 100% | ✅ |
| `src\data\repositories\album_repository.py` | `AlbumRepository.remove_song_from_album` | 100% | ✅ |
| `src\data\repositories\album_repository.py` | `AlbumRepository.get_albums_for_song` | 100% | ✅ |
| `src\data\repositories\contributor_repository.py` | `ContributorRepository.get_by_role` | 100% | ✅ |
| `src\data\repositories\contributor_repository.py` | `ContributorRepository.get_all_aliases` | 66% | ⚠️ |
| `src\data\repositories\contributor_repository.py` | `ContributorRepository.resolve_identity_graph` | 76% | ⚠️ |
| `src\data\repositories\publisher_repository.py` | `PublisherRepository.get_by_id` | 87% | ⚠️ |
| `src\data\repositories\publisher_repository.py` | `PublisherRepository.find_by_name` | 100% | ✅ |
| `src\data\repositories\publisher_repository.py` | `PublisherRepository.create` | 100% | ✅ |
| `src\data\repositories\publisher_repository.py` | `PublisherRepository.get_or_create` | 100% | ✅ |
| `src\data\repositories\publisher_repository.py` | `PublisherRepository.add_publisher_to_album` | 100% | ✅ |
| `src\data\repositories\publisher_repository.py` | `PublisherRepository.remove_publisher_from_album` | 25% | 🔴 |
| `src\data\repositories\publisher_repository.py` | `PublisherRepository.get_publishers_for_album` | 100% | ✅ |
| `src\data\repositories\publisher_repository.py` | `PublisherRepository.get_with_descendants` | 100% | ✅ |
| `src\data\repositories\song_repository.py` | `SongRepository.__init__` | 75% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.insert` | 100% | ✅ |
| `src\data\repositories\song_repository.py` | `SongRepository.get_all` | 75% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.delete` | 66% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.update` | 84% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.update_status` | 66% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository._sync_contributor_roles` | 86% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository._sync_album` | 77% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository._sync_publisher` | 86% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository._sync_genre` | 87% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.get_by_performer` | 75% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.get_by_composer` | 75% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.get_by_unified_artist` | 50% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.get_by_unified_artists` | 6% | 🔴 |
| `src\data\repositories\song_repository.py` | `SongRepository.get_by_id` | 52% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.get_by_path` | 65% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.get_all_years` | 11% | 🔴 |
| `src\data\repositories\song_repository.py` | `SongRepository.get_by_year` | 75% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.get_by_status` | 76% | ⚠️ |
| `src\data\repositories\song_repository.py` | `SongRepository.get_by_isrc` | 8% | 🔴 |
| `src\data\repositories\song_repository.py` | `SongRepository.get_by_audio_hash` | 8% | 🔴 |
| `src\data\repositories\tag_repository.py` | `TagRepository.get_by_id` | 12% | 🔴 |
| `src\data\repositories\tag_repository.py` | `TagRepository.find_by_name` | 83% | ⚠️ |
| `src\data\repositories\tag_repository.py` | `TagRepository.create` | 100% | ✅ |
| `src\data\repositories\tag_repository.py` | `TagRepository.get_or_create` | 100% | ✅ |
| `src\data\repositories\tag_repository.py` | `TagRepository.add_tag_to_source` | 100% | ✅ |
| `src\data\repositories\tag_repository.py` | `TagRepository.remove_tag_from_source` | 100% | ✅ |
| `src\data\repositories\tag_repository.py` | `TagRepository.remove_all_tags_from_source` | 12% | 🔴 |
| `src\data\repositories\tag_repository.py` | `TagRepository.get_tags_for_source` | 100% | ✅ |
| `src\data\repositories\tag_repository.py` | `TagRepository.get_all_by_category` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._init_ui` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._setup_connections` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._setup_shortcuts` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._on_playlist_changed` | 33% | 🔴 |
| `src\presentation\views\main_window.py` | `MainWindow._add_to_playlist` | 11% | 🔴 |
| `src\presentation\views\main_window.py` | `MainWindow._remove_from_playlist` | 25% | 🔴 |
| `src\presentation\views\main_window.py` | `MainWindow._play_item` | 14% | 🔴 |
| `src\presentation\views\main_window.py` | `MainWindow._toggle_play_pause` | 50% | ⚠️ |
| `src\presentation\views\main_window.py` | `MainWindow._play_next` | 8% | 🔴 |
| `src\presentation\views\main_window.py` | `MainWindow._on_volume_changed` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._on_media_status_changed` | 33% | 🔴 |
| `src\presentation\views\main_window.py` | `MainWindow._update_song_label` | 14% | 🔴 |
| `src\presentation\views\main_window.py` | `MainWindow.closeEvent` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._load_window_geometry` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._save_window_geometry` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._load_splitter_states` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._save_splitter_states` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._restore_volume` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._save_volume` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._restore_playlist` | 42% | 🔴 |
| `src\presentation\views\main_window.py` | `MainWindow._save_playlist` | 50% | ⚠️ |
| `src\presentation\views\main_window.py` | `MainWindow._restore_right_panel_tab` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._on_right_tab_changed` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._on_library_selection_changed` | 83% | ⚠️ |
| `src\presentation\views\main_window.py` | `MainWindow._get_selected_song_object` | 100% | ✅ |
| `src\presentation\views\main_window.py` | `MainWindow._on_side_panel_save_requested` | 1% | 🔴 |
| `src\presentation\views\main_window.py` | `MainWindow._auto_advance_selection` | 7% | 🔴 |
| `src\presentation\views\main_window.py` | `MainWindow._get_yellberus_field` | 33% | 🔴 |
| `src\presentation\widgets\filter_widget.py` | `FilterWidget._init_ui` | 100% | ✅ |
| `src\presentation\widgets\filter_widget.py` | `FilterWidget.populate` | 100% | ✅ |
| `src\presentation\widgets\filter_widget.py` | `FilterWidget._add_list_filter` | 64% | ⚠️ |
| `src\presentation\widgets\filter_widget.py` | `FilterWidget._add_grouped_items` | 23% | 🔴 |
| `src\presentation\widgets\filter_widget.py` | `FilterWidget._add_alpha_grouped_items` | 4% | 🔴 |
| `src\presentation\widgets\filter_widget.py` | `FilterWidget._add_boolean_filter` | 100% | ✅ |
| `src\presentation\widgets\filter_widget.py` | `FilterWidget._add_range_filter` | 100% | ✅ |
| `src\presentation\widgets\filter_widget.py` | `FilterWidget._get_field_values` | 55% | ⚠️ |
| `src\presentation\widgets\filter_widget.py` | `FilterWidget._on_tree_clicked` | 93% | ✅ |
| `src\presentation\widgets\filter_widget.py` | `FilterWidget._on_tree_double_clicked` | 72% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `DropIndicatorHeaderView.mousePressEvent` | 33% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `DropIndicatorHeaderView.mouseReleaseEvent` | 20% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `DropIndicatorHeaderView.mouseMoveEvent` | 16% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `DropIndicatorHeaderView._calculate_drop_position` | 8% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `DropIndicatorHeaderView.paintEvent` | 11% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryFilterProxyModel.setTypeFilter` | 100% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryFilterProxyModel.filterAcceptsRow` | 83% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `EventFilterProxy.eventFilter` | 80% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._init_ui` | 100% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.handle_filtered_event` | 30% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._update_empty_label_position` | 50% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.dragEnterEvent` | 75% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.dragLeaveEvent` | 33% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.dropEvent` | 54% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._process_zip_file` | 75% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._setup_top_controls` | 100% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._setup_connections` | 100% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.load_library` | 85% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.update_dirty_rows` | 5% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._apply_incomplete_view_columns` | 16% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._on_type_tab_changed` | 100% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._update_tab_counts` | 100% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._populate_table` | 90% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._format_duration` | 71% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._filter_by_performer` | 33% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._filter_by_unified_artist` | 33% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._filter_by_composer` | 33% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._filter_by_year` | 33% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._filter_by_status` | 33% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._filter_by_field` | 4% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._import_file` | 54% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.import_files_list` | 100% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._import_files` | 12% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.scan_directory` | 9% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._scan_folder` | 12% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._on_search` | 100% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._get_colored_icon` | 92% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._show_table_context_menu` | 58% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._show_column_context_menu` | 5% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._toggle_column_visibility` | 33% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._reset_column_layout` | 8% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._on_column_moved` | 33% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._on_column_resized` | 66% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._load_column_layout` | 90% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._save_column_layout` | 90% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._load_column_visibility_states` | 77% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._save_column_visibility_states` | 50% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.mark_selection_done` | 50% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.save_selected_songs` | 3% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.focus_search` | 33% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._toggle_status` | 71% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.rename_selection` | 16% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._delete_selected` | 92% | ✅ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._on_table_double_click` | 50% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._emit_add_to_playlist` | 7% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._show_id3_tags` | 75% | ⚠️ |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._handle_metadata_import` | 6% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._handle_metadata_export` | 12% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget.rename_selection` | 2% | 🔴 |
| `src\presentation\widgets\library_widget.py` | `LibraryWidget._get_incomplete_fields` | 100% | ✅ |
| `src\presentation\widgets\metadata_viewer_dialog.py` | `MetadataViewerDialog._init_ui` | 100% | ✅ |
| `src\presentation\widgets\metadata_viewer_dialog.py` | `MetadataViewerDialog._update_button_state` | 100% | ✅ |
| `src\presentation\widgets\metadata_viewer_dialog.py` | `MetadataViewerDialog._on_import_clicked` | 33% | 🔴 |
| `src\presentation\widgets\metadata_viewer_dialog.py` | `MetadataViewerDialog._on_export_clicked` | 33% | 🔴 |
| `src\presentation\widgets\metadata_viewer_dialog.py` | `MetadataViewerDialog._populate_table` | 73% | ⚠️ |
| `src\presentation\widgets\metadata_viewer_dialog.py` | `MetadataViewerDialog._add_section_header` | 100% | ✅ |
| `src\presentation\widgets\metadata_viewer_dialog.py` | `MetadataViewerDialog._add_row` | 79% | ⚠️ |
| `src\presentation\widgets\metadata_viewer_dialog.py` | `MetadataViewerDialog._format_value` | 66% | ⚠️ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget._init_ui` | 100% | ✅ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget._sync_crossfade_combo` | 100% | ✅ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget._on_crossfade_combo_changed` | 100% | ✅ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget._setup_connections` | 100% | ✅ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget._on_crossfade_started` | 33% | 🔴 |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget._on_crossfade_finished` | 33% | 🔴 |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget.set_playlist_count` | 100% | ✅ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget._update_skip_button_state` | 100% | ✅ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget.update_play_button_state` | 100% | ✅ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget.update_duration` | 25% | 🔴 |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget.update_position` | 100% | ✅ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget.update_song_label` | 50% | ⚠️ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget._format_time` | 100% | ✅ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget.set_volume` | 100% | ✅ |
| `src\presentation\widgets\playback_control_widget.py` | `PlaybackControlWidget.get_volume` | 100% | ✅ |
| `src\presentation\widgets\playlist_widget.py` | `PlaylistItemDelegate.paint` | 100% | ✅ |
| `src\presentation\widgets\playlist_widget.py` | `PlaylistItemDelegate.sizeHint` | 100% | ✅ |
| `src\presentation\widgets\playlist_widget.py` | `PlaylistWidget.mimeData` | 5% | 🔴 |
| `src\presentation\widgets\playlist_widget.py` | `PlaylistWidget.dragEnterEvent` | 94% | ✅ |
| `src\presentation\widgets\playlist_widget.py` | `PlaylistWidget.dragMoveEvent` | 100% | ✅ |
| `src\presentation\widgets\playlist_widget.py` | `PlaylistWidget.dragLeaveEvent` | 100% | ✅ |
| `src\presentation\widgets\playlist_widget.py` | `PlaylistWidget.dropEvent` | 96% | ✅ |
| `src\presentation\widgets\playlist_widget.py` | `PlaylistWidget.paintEvent` | 100% | ✅ |
| `src\presentation\widgets\seek_slider.py` | `SeekSlider.updateDuration` | 100% | ✅ |
| `src\presentation\widgets\seek_slider.py` | `SeekSlider.enterEvent` | 100% | ✅ |
| `src\presentation\widgets\seek_slider.py` | `SeekSlider.mouseMoveEvent` | 100% | ✅ |
| `src\presentation\widgets\seek_slider.py` | `SeekSlider.mousePressEvent` | 100% | ✅ |
| `src\presentation\widgets\seek_slider.py` | `SeekSlider._update_tooltip` | 100% | ✅ |
| `src\presentation\widgets\seek_slider.py` | `SeekSlider.sizeHint` | 100% | ✅ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._init_ui` | 100% | ✅ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget.set_songs` | 100% | ✅ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._update_header` | 69% | ⚠️ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._build_fields` | 93% | ✅ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._create_field_widget` | 84% | ⚠️ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._validate_isrc_field` | 80% | ⚠️ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._calculate_bulk_value` | 46% | 🔴 |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._get_effective_value` | 75% | ⚠️ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._on_field_changed` | 12% | 🔴 |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._on_done_toggled` | 50% | ⚠️ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._validate_done_gate` | 93% | ✅ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._update_save_state` | 100% | ✅ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._on_save_clicked` | 77% | ⚠️ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget.trigger_save` | 33% | 🔴 |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._on_discard_clicked` | 25% | 🔴 |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget.clear_staged` | 12% | 🔴 |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._clear_fields` | 50% | ⚠️ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget.eventFilter` | 100% | ✅ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._get_staged_song` | 45% | 🔴 |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget._update_projected_path` | 66% | ⚠️ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget.add_group` | 95% | ✅ |
| `src\presentation\widgets\side_panel_widget.py` | `SidePanelWidget.make_style` | 100% | ✅ |
| `src\utils\audio_hash.py` | `calculate_audio_hash` | 96% | ✅ |
| `src\utils\validation.py` | `sanitize_isrc` | 100% | ✅ |
| `src\utils\validation.py` | `validate_isrc` | 80% | ⚠️ |