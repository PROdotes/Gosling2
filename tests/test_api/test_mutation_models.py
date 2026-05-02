"""
Unit tests for MutationRequest Pydantic models.
No DB, no HTTP — validates shape, 422 rules, and null/absent/empty semantics.
"""
import pytest
from pydantic import ValidationError

from src.engine.routers.mutation_models import MutationRequest


def valid(**kwargs) -> dict:
    """Minimal valid request with one update item, overridable."""
    base = {"update": [{"type": "song", "id": 1}]}
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# Top-level: empty request
# ---------------------------------------------------------------------------

class TestEmptyRequest:
    def test_all_buckets_absent_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({})

    def test_all_buckets_empty_lists_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"add": [], "update": [], "remove": []})

    def test_single_add_item_ok(self):
        MutationRequest.model_validate({
            "add": [{"type": "credit", "song_id": 1, "name": "Freddie Mercury", "id": 1, "role": "Performer"}]
        })


# ---------------------------------------------------------------------------
# Add items
# ---------------------------------------------------------------------------

class TestAddCreditItem:
    def test_valid(self):
        MutationRequest.model_validate({
            "add": [{"type": "credit", "song_id": 1, "name": "Freddie", "id": 1, "role": "Performer"}]
        })

    def test_id_null_allowed(self):
        MutationRequest.model_validate({
            "add": [{"type": "credit", "song_id": 1, "name": "Freddie", "id": None, "role": "Performer"}]
        })

    def test_id_absent_allowed(self):
        MutationRequest.model_validate({
            "add": [{"type": "credit", "song_id": 1, "name": "Freddie", "role": "Performer"}]
        })

    def test_blank_name_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({
                "add": [{"type": "credit", "song_id": 1, "name": "   ", "role": "Performer"}]
            })

    def test_blank_role_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({
                "add": [{"type": "credit", "song_id": 1, "name": "Freddie", "role": ""}]
            })


class TestAddTagItem:
    def test_valid(self):
        MutationRequest.model_validate({
            "add": [{"type": "tag", "song_id": 1, "name": "Rock", "category": "Genre"}]
        })

    def test_make_primary_defaults_false(self):
        req = MutationRequest.model_validate({
            "add": [{"type": "tag", "song_id": 1, "name": "Rock", "category": "Genre"}]
        })
        assert req.add[0].make_primary is False

    def test_blank_category_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({
                "add": [{"type": "tag", "song_id": 1, "name": "Rock", "category": ""}]
            })


class TestAddAlbumItem:
    def test_valid_with_track(self):
        MutationRequest.model_validate({
            "add": [{"type": "album", "song_id": 1, "name": "A Night at the Opera", "id": 3, "track_number": 1, "disc_number": 1}]
        })

    def test_track_disc_optional(self):
        MutationRequest.model_validate({
            "add": [{"type": "album", "song_id": 1, "name": "A Night at the Opera"}]
        })


# ---------------------------------------------------------------------------
# Update items
# ---------------------------------------------------------------------------

class TestUpdateSongItem:
    def test_id_only_valid(self):
        MutationRequest.model_validate({"update": [{"type": "song", "id": 1}]})

    def test_all_fields(self):
        MutationRequest.model_validate({"update": [
            {"type": "song", "id": 1, "media_name": "Title", "bpm": 120,
             "year": 1975, "isrc": "GBAYE0000001", "is_active": True, "notes": "note"}
        ]})

    def test_empty_string_media_name_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1, "media_name": ""}]})

    def test_null_media_name_allowed(self):
        # null = clear the field; absent = leave alone — both valid at model layer
        MutationRequest.model_validate({"update": [{"type": "song", "id": 1, "media_name": None}]})

    def test_invalid_isrc_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1, "isrc": "bad"}]})

    def test_valid_isrc(self):
        MutationRequest.model_validate({"update": [{"type": "song", "id": 1, "isrc": "GBAYE0000001"}]})

    def test_zero_bpm_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1, "bpm": 0}]})

    def test_negative_bpm_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1, "bpm": -1}]})

    def test_year_out_of_range_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"update": [{"type": "song", "id": 1, "year": 99}]})

    def test_year_valid(self):
        MutationRequest.model_validate({"update": [{"type": "song", "id": 1, "year": 2024}]})


class TestUpdateTagItems:
    def test_tag_entity_update(self):
        MutationRequest.model_validate({"update": [{"type": "tag", "id": 5, "name": "Rock", "category": "Genre"}]})

    def test_tag_entity_empty_name_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"update": [{"type": "tag", "id": 5, "name": ""}]})

    def test_song_tag_update(self):
        MutationRequest.model_validate({"update": [{"type": "song_tag", "song_id": 1, "tag_id": 5, "is_primary": True}]})


class TestUpdateAlbumItems:
    def test_album_entity_update(self):
        MutationRequest.model_validate({"update": [
            {"type": "album", "id": 3, "title": "A Night at the Opera", "album_type": "LP", "release_year": 1975}
        ]})

    def test_album_entity_bad_year_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"update": [{"type": "album", "id": 3, "release_year": 75}]})

    def test_song_album_update(self):
        MutationRequest.model_validate({"update": [
            {"type": "song_album", "song_id": 1, "album_id": 3, "track_number": 5, "disc_number": 1}
        ]})


class TestUpdatePublisherItem:
    def test_valid(self):
        MutationRequest.model_validate({"update": [{"type": "publisher", "id": 9, "name": "EMI", "parent_id": 12}]})

    def test_empty_name_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"update": [{"type": "publisher", "id": 9, "name": ""}]})

    def test_null_name_allowed(self):
        MutationRequest.model_validate({"update": [{"type": "publisher", "id": 9, "name": None}]})


class TestUpdateCreditItem:
    def test_valid(self):
        MutationRequest.model_validate({"update": [{"type": "credit", "id": 1, "display_name": "F. Mercury"}]})

    def test_empty_display_name_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"update": [{"type": "credit", "id": 1, "display_name": ""}]})


# ---------------------------------------------------------------------------
# Remove items
# ---------------------------------------------------------------------------

class TestRemoveItems:
    def test_remove_credit(self):
        MutationRequest.model_validate({"remove": [{"type": "credit", "song_id": 1, "id": 42}]})

    def test_remove_tag(self):
        MutationRequest.model_validate({"remove": [{"type": "tag", "song_id": 1, "id": 7}]})

    def test_remove_publisher(self):
        MutationRequest.model_validate({"remove": [{"type": "publisher", "song_id": 1, "id": 3}]})

    def test_remove_album(self):
        MutationRequest.model_validate({"remove": [{"type": "album", "song_id": 1, "id": 5}]})

    def test_missing_id_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"remove": [{"type": "credit", "song_id": 1}]})


# ---------------------------------------------------------------------------
# Mixed buckets + discriminator coverage
# ---------------------------------------------------------------------------

class TestMixedRequest:
    def test_full_mixed_request(self):
        MutationRequest.model_validate({
            "add": [
                {"type": "credit", "song_id": 1, "name": "Freddie Mercury", "id": 1, "role": "Performer"},
                {"type": "tag", "song_id": 1, "name": "Rock", "id": 5, "category": "Genre"},
                {"type": "publisher", "song_id": 1, "name": "EMI", "id": None},
                {"type": "album", "song_id": 1, "name": "A Night at the Opera", "id": 3, "track_number": 1},
            ],
            "update": [
                {"type": "song", "id": 1, "media_name": "Bohemian Rhapsody", "bpm": 120},
                {"type": "song_tag", "song_id": 1, "tag_id": 5, "is_primary": True},
                {"type": "song_album", "song_id": 1, "album_id": 3, "track_number": 5},
                {"type": "album", "id": 3, "title": "A Night at the Opera"},
                {"type": "credit", "id": 1, "display_name": "F. Mercury"},
                {"type": "publisher", "id": 9, "name": "EMI"},
                {"type": "tag", "id": 5, "name": "Rock", "category": "Genre"},
            ],
            "remove": [
                {"type": "credit", "song_id": 1, "id": 42},
                {"type": "tag", "song_id": 1, "id": 7},
            ],
        })

    def test_unknown_type_422(self):
        with pytest.raises(ValidationError):
            MutationRequest.model_validate({"add": [{"type": "unknown_entity", "song_id": 1}]})
