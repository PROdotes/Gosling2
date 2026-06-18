"""Tests for the runtime settings model (src/services/config_service.py).

JSON is the source of truth: load_settings_from reads it (missing keys fall back
to field defaults, a corrupt/invalid file falls back to defaults + a warning),
save_settings validates a patch then persists the full settings and mutates the
live instance in place, and reload_settings re-reads the file into the live
instance at boot.
"""

import json

import pytest

from src.engine import config
from src.services import config_service
from src.services.config_service import (
    Settings,
    load_settings_from,
    reload_settings,
    save_settings,
    settings,
)

FIELD_NAMES = set(Settings.model_fields)


def _write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


@pytest.fixture
def restore_settings():
    """Snapshot and restore every field on the live settings instance, so a test
    that calls save_settings/reload_settings (which mutate the singleton) never
    leaks into another test."""
    saved = settings.model_dump()
    yield
    for name, value in saved.items():
        setattr(settings, name, value)


# --------------------------------------------------------------------------
# Settings model: defaults and field set
# --------------------------------------------------------------------------
class TestSettingsModel:
    def test_default_instance_has_expected_fields(self):
        s = Settings()
        assert set(s.model_dump()) == {
            "library_root",
            "wav_auto_convert",
            "auto_move_on_approve",
            "prompt_before_move",
            "auto_save_id3",
            "scrubber_auto_play",
            "blur_saves_scalars",
            "default_search_engine",
        }

    def test_defaults_are_typed(self):
        s = Settings()
        assert isinstance(s.wav_auto_convert, bool)
        assert isinstance(s.library_root, str)
        assert s.default_search_engine.value == "spotify"


# --------------------------------------------------------------------------
# load_settings_from (pure read)
# --------------------------------------------------------------------------
class TestLoadSettingsFrom:
    def test_missing_file_returns_defaults_no_warnings(self, tmp_path):
        loaded, warnings = load_settings_from(tmp_path / "settings.json")
        assert loaded.model_dump() == Settings().model_dump()
        assert warnings == []

    def test_partial_file_overrides_only_that_key(self, tmp_path):
        default = Settings()
        path = _write(
            tmp_path / "settings.json",
            {"wav_auto_convert": not default.wav_auto_convert},
        )
        loaded, warnings = load_settings_from(path)
        assert loaded.wav_auto_convert == (not default.wav_auto_convert)
        assert loaded.auto_save_id3 == default.auto_save_id3
        assert warnings == []

    def test_unknown_key_in_file_is_ignored(self, tmp_path):
        path = _write(
            tmp_path / "settings.json",
            {"totally_made_up_key": 123, "scrubber_auto_play": False},
        )
        loaded, warnings = load_settings_from(path)
        assert "totally_made_up_key" not in loaded.model_dump()
        assert loaded.scrubber_auto_play is False
        assert warnings == []

    def test_corrupt_file_returns_defaults_with_warning(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text("{ this is not json", encoding="utf-8")
        loaded, warnings = load_settings_from(path)
        assert loaded.model_dump() == Settings().model_dump()
        assert len(warnings) == 1
        assert warnings[0]["kind"] == "settings_load"
        assert warnings[0].get("error")

    def test_invalid_value_in_file_returns_defaults_with_warning(self, tmp_path):
        # A wrong-typed value the model rejects falls back like a corrupt file.
        path = _write(tmp_path / "settings.json", {"wav_auto_convert": "not-a-bool"})
        loaded, warnings = load_settings_from(path)
        assert loaded.model_dump() == Settings().model_dump()
        assert len(warnings) == 1
        assert warnings[0]["kind"] == "settings_load"


# --------------------------------------------------------------------------
# save_settings (validate -> persist full file -> mutate live instance)
# --------------------------------------------------------------------------
class TestSaveSettings:
    def test_persists_full_settings_to_file(
        self, tmp_path, monkeypatch, restore_settings
    ):
        path = tmp_path / "settings.json"
        monkeypatch.setattr(config, "SETTINGS_PATH", path)
        save_settings({"wav_auto_convert": not settings.wav_auto_convert})
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        # JSON is the source of truth: the written file holds every field.
        assert set(on_disk) == FIELD_NAMES

    def test_mutates_live_instance_in_place(
        self, tmp_path, monkeypatch, restore_settings
    ):
        monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "settings.json")
        target = not settings.auto_save_id3
        save_settings({"auto_save_id3": target})
        assert settings.auto_save_id3 == target

    def test_partial_save_preserves_other_values(
        self, tmp_path, monkeypatch, restore_settings
    ):
        monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "settings.json")
        a = not settings.wav_auto_convert
        b = not settings.scrubber_auto_play
        save_settings({"wav_auto_convert": a})
        save_settings({"scrubber_auto_play": b})
        assert settings.wav_auto_convert == a
        assert settings.scrubber_auto_play == b

    def test_search_engine_string_is_coerced(
        self, tmp_path, monkeypatch, restore_settings
    ):
        monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "settings.json")
        save_settings({"default_search_engine": "youtube"})
        assert settings.default_search_engine.value == "youtube"


class TestSaveValidation:
    def test_unknown_key_raises_and_writes_nothing(
        self, tmp_path, monkeypatch, restore_settings
    ):
        path = tmp_path / "settings.json"
        monkeypatch.setattr(config, "SETTINGS_PATH", path)
        with pytest.raises(ValueError):
            save_settings({"totally_made_up_key": 1})
        assert not path.exists()

    def test_bad_type_raises(self, tmp_path, monkeypatch, restore_settings):
        monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "settings.json")
        with pytest.raises(ValueError):
            save_settings({"auto_save_id3": [1, 2]})

    def test_unknown_search_engine_raises(
        self, tmp_path, monkeypatch, restore_settings
    ):
        monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "settings.json")
        with pytest.raises(ValueError):
            save_settings({"default_search_engine": "altavista"})

    def test_empty_library_root_raises(self, tmp_path, monkeypatch, restore_settings):
        monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "settings.json")
        with pytest.raises(ValueError):
            save_settings({"library_root": ""})

    def test_invalid_save_does_not_mutate_live_instance(
        self, tmp_path, monkeypatch, restore_settings
    ):
        monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "settings.json")
        before = settings.auto_save_id3
        with pytest.raises(ValueError):
            save_settings({"auto_save_id3": [1, 2]})
        assert settings.auto_save_id3 == before


# --------------------------------------------------------------------------
# reload_settings (boot overlay: file -> live instance)
# --------------------------------------------------------------------------
class TestReloadSettings:
    def test_file_value_is_loaded_into_live_instance(
        self, tmp_path, monkeypatch, restore_settings
    ):
        target = not settings.scrubber_auto_play
        path = _write(tmp_path / "settings.json", {"scrubber_auto_play": target})
        monkeypatch.setattr(config, "SETTINGS_PATH", path)
        warnings = reload_settings()
        assert settings.scrubber_auto_play == target
        assert warnings == []

    def test_missing_file_resets_to_defaults(
        self, tmp_path, monkeypatch, restore_settings
    ):
        monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "settings.json")
        reload_settings()
        assert settings.scrubber_auto_play == Settings().scrubber_auto_play

    def test_corrupt_file_warns_and_leaves_defaults(
        self, tmp_path, monkeypatch, restore_settings
    ):
        path = tmp_path / "settings.json"
        path.write_text("{ broken", encoding="utf-8")
        monkeypatch.setattr(config, "SETTINGS_PATH", path)
        warnings = reload_settings()
        assert len(warnings) == 1
        assert warnings[0]["kind"] == "settings_load"
        assert settings.model_dump() == Settings().model_dump()

    def test_save_then_reload_round_trips(
        self, tmp_path, monkeypatch, restore_settings
    ):
        path = tmp_path / "settings.json"
        monkeypatch.setattr(config, "SETTINGS_PATH", path)
        target = not settings.blur_saves_scalars
        save_settings({"blur_saves_scalars": target})
        # Wipe the live value, then prove the persisted file restores it.
        settings.blur_saves_scalars = not target
        reload_settings()
        assert settings.blur_saves_scalars == target


def test_config_service_module_exposes_singleton():
    # Read sites import this exact instance; identity matters.
    assert config_service.settings is settings
    assert isinstance(settings, Settings)
