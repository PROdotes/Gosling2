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


# ---------------------------------------------------------------------------
# Packer (multi_mutate) — pure expansion; coordinator captured, not run
# ---------------------------------------------------------------------------
@pytest.fixture
def captured(monkeypatch):
    box = {}

    class FakeCoordinator:
        def __init__(self, db_path):
            pass

        def apply(self, request):
            box["request"] = request
            return {"songs": [], "warnings": []}

    monkeypatch.setattr(
        "src.services.multi_edit_service.MutationCoordinator", FakeCoordinator
    )
    return box


def test_update_expands_per_song_with_touched_fields_only(service, captured):
    service.multi_mutate([1, 2], update={"year": 2000})
    items = captured["request"].update
    assert [(i.id, i.year) for i in items] == [(1, 2000), (2, 2000)]
    assert all(
        i.model_dump(exclude_unset=True).keys() == {"type", "id", "year"} for i in items
    )


def test_update_rejects_non_collapsed_fields(service, captured):
    with pytest.raises(ValueError, match="processing_status"):
        service.multi_mutate([1, 2], update={"processing_status": 2})


def test_add_is_blind_clone_per_song(service, captured):
    service.multi_mutate([1, 2], add=[{"type": "tag", "id": 3}])
    items = captured["request"].add
    assert [(i.type, i.song_id, i.id) for i in items] == [("tag", 1, 3), ("tag", 2, 3)]


def test_add_album_forces_zero_track_and_disc(service, captured):
    service.multi_mutate([1, 2], add=[{"type": "album", "id": 200, "name": "TCATS"}])
    items = captured["request"].add
    assert all((i.track_number, i.disc_number) == (0, 0) for i in items)


def test_add_rejects_non_song_op_types(service, captured):
    with pytest.raises(ValueError, match="identity_alias"):
        service.multi_mutate([1, 2], add=[{"type": "identity_alias", "identity_id": 1}])


def test_add_invalid_item_shape_raises_value_error(service, captured):
    # credit without a name fails the real AddCreditItem validation
    with pytest.raises(ValueError):
        service.multi_mutate([1, 2], add=[{"type": "credit", "role": "Performer"}])


def test_remove_universal_tag_expands_per_song(service, captured):
    # Grunge(1) is on songs 1 and 9
    service.multi_mutate([1, 9], remove=[{"type": "tag", "id": 1}])
    items = captured["request"].remove
    assert [(i.type, i.song_id, i.id) for i in items] == [("tag", 1, 1), ("tag", 9, 1)]


def test_remove_partial_tag_raises_value_error(service, captured):
    # Energetic(2) is on song 1 only
    with pytest.raises(ValueError, match="not universal"):
        service.multi_mutate([1, 9], remove=[{"type": "tag", "id": 2}])


def test_remove_absent_tag_raises_lookup_error(service, captured):
    with pytest.raises(LookupError, match="999"):
        service.multi_mutate([1, 9], remove=[{"type": "tag", "id": 999}])


def test_remove_credit_resolves_per_song_row_ids(service, captured):
    # Dave Grohl(10) is Performer on songs 6 and 8, via different credit rows.
    songs = {s.id: s for s in service._load_songs([6, 8])}
    own_row = {
        sid: next(
            c.credit_id
            for c in s.credits
            if c.name_id == 10 and c.role_name == "Performer"
        )
        for sid, s in songs.items()
    }
    # The virtual view hands the frontend one song's credit_id; either works.
    service.multi_mutate([6, 8], remove=[{"type": "credit", "id": own_row[6]}])
    items = captured["request"].remove
    assert {(i.song_id, i.id) for i in items} == {
        (6, own_row[6]),
        (8, own_row[8]),
    }


def test_remove_partial_credit_raises_value_error(service, captured):
    # Taylor(40) is Composer on song 6 but Performer on song 8 — the
    # (name_id, role) pair is not universal.
    song6 = service._load_songs([6])[0]
    taylor_composer = next(
        c.credit_id
        for c in song6.credits
        if c.name_id == 40 and c.role_name == "Composer"
    )
    with pytest.raises(ValueError, match="not universal"):
        service.multi_mutate([6, 8], remove=[{"type": "credit", "id": taylor_composer}])


def test_remove_unknown_credit_raises_lookup_error(service, captured):
    with pytest.raises(LookupError, match="99999"):
        service.multi_mutate([6, 8], remove=[{"type": "credit", "id": 99999}])


def test_empty_ops_is_noop_without_coordinator_call(service, captured):
    result = service.multi_mutate([1, 2], update={})
    assert result == {"songs": [], "warnings": []}
    assert "request" not in captured
