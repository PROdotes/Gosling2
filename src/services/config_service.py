"""Runtime settings.

This module defines the editable runtime settings and exposes them to the
frontend. A setting is one typed field on the ``Settings`` model: its type,
default, and validation all live on the field, so adding a setting is a one-line
change that is automatically persisted, readable everywhere via the live
``settings`` instance, and rendered in the editor (the form is generated from
``Settings.model_json_schema()``).

``json/settings.json`` is the source of truth; the ``settings`` instance is the
in-memory mirror. Immutable code facts (paths, enums like ProcessingStatus,
SCALAR_VALIDATION) stay in ``config.py`` and are never part of this surface.
"""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.engine import config


class SearchEngine(str, Enum):
    """The external search engines a song can be looked up on. Declares the
    option set for the ``default_search_engine`` select; model_json_schema
    exposes these values to the editor form."""

    spotify = "spotify"
    google = "google"
    youtube = "youtube"
    musicbrainz = "musicbrainz"


# Display labels for the search engines, consumed by the song-editor search UI
# (served via /api/v1/config and /api/v1/validation-rules).
SEARCH_ENGINE_LABELS: dict[str, str] = {
    SearchEngine.spotify.value: "Spotify",
    SearchEngine.google.value: "Google",
    SearchEngine.youtube.value: "YouTube",
    SearchEngine.musicbrainz.value: "MusicBrainz",
}


class Settings(BaseModel):
    """The editable runtime settings. One typed field per setting."""

    model_config = ConfigDict(validate_assignment=True)

    library_root: str = Field(default="Z:\\Songs", title="Library root", min_length=1)
    wav_auto_convert: bool = Field(
        default=True, title="Auto-convert WAV to MP3 on ingest"
    )
    auto_move_on_approve: bool = Field(
        default=True, title="Auto-move file to library on approve"
    )
    prompt_before_move: bool = Field(default=True, title="Prompt before moving files")
    auto_save_id3: bool = Field(default=True, title="Auto-save ID3 tags on edit")
    scrubber_auto_play: bool = Field(default=True, title="Auto-play in the scrubber")
    blur_saves_scalars: bool = Field(default=True, title="Save scalar fields on blur")
    default_search_engine: SearchEngine = Field(
        default=SearchEngine.spotify, title="Default search engine"
    )


def load_settings_from(path: Path) -> tuple["Settings", list[dict]]:
    """Read settings from ``path``. A missing file is the legitimate default
    state (all field defaults). A file that exists but is not valid for the model
    falls back to defaults and records a warning surfaced to the UI as a banner.

    JSON is the source of truth; keys absent from the file fall back to their
    field defaults, and unknown keys are ignored.
    """
    if not path.exists():
        return Settings(), []
    try:
        text = path.read_text(encoding="utf-8-sig")
        return Settings.model_validate_json(text), []
    except Exception as e:  # any parse/validation error -> banner, not a crash
        return Settings(), [{"kind": "settings_load", "error": str(e)}]


# The single live settings instance. Read sites import this and read settings.x,
# analogous to reading config.X. It starts at field defaults and is populated
# from json/settings.json by reload_settings() at server startup; POSTs mutate it
# in place. Tests keep it at defaults (hermetic) and monkeypatch attributes.
settings = Settings()


def reload_settings() -> list[dict]:
    """Re-read json/settings.json into the live settings instance. Called at
    server startup so persisted values take effect on boot. Returns any load
    warnings (a corrupt file leaves the live instance at defaults)."""
    fresh, warnings = load_settings_from(config.SETTINGS_PATH)
    for name in Settings.model_fields:
        setattr(settings, name, getattr(fresh, name))
    return warnings


def save_settings(patch: dict) -> Settings:
    """Validate a partial settings dict, persist the full settings to
    json/settings.json, and update the live instance in place so the change
    takes effect without a restart. Unknown keys or values that fail field
    validation raise (ValueError / pydantic ValidationError, the latter a
    ValueError subclass) and write nothing.
    """
    unknown = set(patch) - set(Settings.model_fields)
    if unknown:
        raise ValueError(f"Unknown setting(s): {', '.join(sorted(unknown))}")
    merged = settings.model_dump()
    merged.update(patch)
    validated = Settings.model_validate(merged)  # raises on bad type/value

    config.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.SETTINGS_PATH.write_text(
        validated.model_dump_json(indent=2), encoding="utf-8"
    )
    for name in Settings.model_fields:
        setattr(settings, name, getattr(validated, name))
    return settings
