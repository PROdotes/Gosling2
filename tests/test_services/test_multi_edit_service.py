"""
MultiEditService collapser tests (multi-song virtual SongView).

Fixture facts used (see conftest data map):
  Song 1: "Smells Like Teen Spirit" year=1991, Nirvana(20) Performer,
          tags Grunge(1)/Energetic(2)/English(5), album Nevermind(100),
          publisher DGC Records(10)
  Song 2: "Everlong" year=1997, Foo Fighters(30) Performer,
          tags 90s(3)/Rock(7), album TCATS(200)
  Song 6: "Dual Credit Track" Dave Grohl(10) Performer + Taylor(40) Composer
  Song 7: "Hollow Song" bpm=128, isrc=ISRC123
  Song 8: "Joint Venture" Dave Grohl(10) Performer + Taylor(40) Performer
  Song 9: "Priority Test" tags Grunge(1) + Alt Rock(6)
"""

import pytest

from src.services.multi_edit_service import MultiEditService


@pytest.fixture
def service(populated_db):
    return MultiEditService(populated_db)


# ---------------------------------------------------------------------------
# Scalars
# ---------------------------------------------------------------------------
def test_agreed_scalar_passes_through(service):
    view = service.get_multi_view([1, 2])
    # both songs have bpm=None -> agreed, not mixed
    assert view.bpm is None
    assert "bpm" not in view.mixed_fields


def test_mixed_scalar_is_null_and_listed(service):
    view = service.get_multi_view([1, 2])
    assert view.year is None
    assert view.mixed_fields["year"] == [1991, 1997]
    assert view.media_name == ""
    assert view.mixed_fields["media_name"] == [
        "Smells Like Teen Spirit",
        "Everlong",
    ]


def test_mixed_with_empty_includes_none(service):
    # song 1 bpm=None, song 7 bpm=128
    view = service.get_multi_view([1, 7])
    assert view.bpm is None
    assert view.mixed_fields["bpm"] == [None, 128]
    assert view.mixed_fields["isrc"] == [None, "ISRC123"]


def test_agreed_display_fields_pass_through(service):
    # Display-only fields (not in mixed_fields) follow the same agree -> value
    # rule so identical songs render identically to a single selection.
    view = service.get_multi_view([1, 1])
    single = service.get_multi_view([1])
    assert view.processing_status == single.processing_status
    assert view.is_active == single.is_active


def test_mixed_display_fields_fall_back_to_defaults(service):
    songs = service._song_repo.get_by_ids([1, 2])
    statuses = {s.processing_status for s in songs}
    view = service.get_multi_view([1, 2])
    if len(statuses) == 1:
        assert view.processing_status == statuses.pop()
    else:
        assert view.processing_status is None
    assert "processing_status" not in view.mixed_fields
    assert "is_active" not in view.mixed_fields


def test_single_song_selection_has_no_mixed_fields(service):
    view = service.get_multi_view([1, 1])  # dupes collapse to one song
    assert view.mixed_fields == {}
    assert view.media_name == "Smells Like Teen Spirit"
    assert view.year == 1991


# ---------------------------------------------------------------------------
# Credits
# ---------------------------------------------------------------------------
def test_shared_credit_is_universal(service):
    view = service.get_multi_view([6, 8])
    dave = [c for c in view.credits if c.name_id == 10]
    assert len(dave) == 1
    assert dave[0].role_name == "Performer"
    assert dave[0].universal is True


def test_same_name_different_role_are_separate_entries(service):
    # Taylor(40): Composer on song 6, Performer on song 8
    view = service.get_multi_view([6, 8])
    taylor = [c for c in view.credits if c.name_id == 40]
    assert {(c.role_name, c.universal) for c in taylor} == {
        ("Composer", False),
        ("Performer", False),
    }


def test_disjoint_credits_are_partial(service):
    view = service.get_multi_view([1, 2])
    assert {(c.name_id, c.universal) for c in view.credits} == {
        (20, False),
        (30, False),
    }


# ---------------------------------------------------------------------------
# Tags / publishers / albums
# ---------------------------------------------------------------------------
def test_shared_tag_is_universal_others_partial(service):
    # Grunge(1) on songs 1 and 9; everything else on one song only
    view = service.get_multi_view([1, 9])
    by_id = {t.id: t for t in view.tags}
    assert by_id[1].universal is True
    assert by_id[2].universal is False  # Energetic, song 1 only
    assert by_id[6].universal is False  # Alt Rock, song 9 only


def test_tags_are_union_without_duplicates(service):
    view = service.get_multi_view([1, 9])
    assert sorted(t.id for t in view.tags) == [1, 2, 5, 6]


def test_publishers_partial(service):
    # only song 1 has a recording publisher (DGC Records)
    view = service.get_multi_view([1, 2])
    assert [(p.id, p.universal) for p in view.publishers] == [(10, False)]


def test_albums_partial(service):
    view = service.get_multi_view([1, 2])
    assert {(a.album_id, a.universal) for a in view.albums} == {
        (100, False),
        (200, False),
    }


# ---------------------------------------------------------------------------
# Shape / errors
# ---------------------------------------------------------------------------
def test_virtual_song_has_no_identity_or_file(service):
    view = service.get_multi_view([1, 2])
    assert view.id is None
    assert view.source_path == ""
    assert view.duration_s == 0


def test_missing_song_raises_lookup_error(service):
    with pytest.raises(LookupError, match="999"):
        service.get_multi_view([1, 999])
