"""
Tests for CreditMutator — add/remove/update song credits.

Uses populated_db (songs 1-9, Dave Grohl fixture).

Data map used here:
  Song 6: Dave Grohl(NameID=10) Performer + Taylor(NameID=40) Composer
  Song 7: ZERO credits
  IdentityID=1: Dave Grohl  IdentityID=4: Taylor Hawkins
  RoleID=1: Performer  RoleID=2: Composer
  CreditIDs are fetched at runtime since they're auto-assigned.
"""
import sqlite3

import pytest

from src.engine.routers.mutation_models import (
    AddCreditItem,
    RemoveCreditItem,
    UpdateCreditEntityItem,
)
from src.services.mutators.credit_mutator import CreditMutator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    return conn


def _get_credits(conn: sqlite3.Connection, song_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT sc.CreditID, an.DisplayName, r.RoleName, an.OwnerIdentityID
        FROM SongCredits sc
        JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
        JOIN Roles r ON sc.RoleID = r.RoleID
        WHERE sc.SourceID = ?
        """,
        (song_id,),
    ).fetchall()


def _get_credit_id(conn: sqlite3.Connection, song_id: int, name: str, role: str) -> int:
    row = conn.execute(
        """
        SELECT sc.CreditID FROM SongCredits sc
        JOIN ArtistNames an ON sc.CreditedNameID = an.NameID
        JOIN Roles r ON sc.RoleID = r.RoleID
        WHERE sc.SourceID = ? AND an.DisplayName = ? COLLATE UTF8_NOCASE AND r.RoleName = ?
        """,
        (song_id, name, role),
    ).fetchone()
    assert row is not None, f"Credit not found: song={song_id} name={name} role={role}"
    return row["CreditID"]


def _get_display_name(conn: sqlite3.Connection, name_id: int) -> str:
    row = conn.execute("SELECT DisplayName FROM ArtistNames WHERE NameID = ?", (name_id,)).fetchone()
    assert row is not None
    return row["DisplayName"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mutator(populated_db):
    return CreditMutator(populated_db)


@pytest.fixture
def conn(populated_db):
    c = _make_conn(populated_db)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

class TestCreditMutatorAdd:
    def test_add_new_name_creates_credit(self, mutator, conn):
        item = AddCreditItem.model_validate(
            {"type": "credit", "song_id": 7, "name": "Brand New Artist", "role": "Performer"}
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        credits = _get_credits(conn, 7)
        assert any(c["DisplayName"] == "Brand New Artist" and c["RoleName"] == "Performer" for c in credits)

    def test_add_with_identity_id_links_correctly(self, mutator, conn):
        item = AddCreditItem.model_validate(
            {"type": "credit", "song_id": 7, "name": "Dave Grohl", "role": "Composer", "id": 1}
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        credits = _get_credits(conn, 7)
        match = next((c for c in credits if c["DisplayName"] == "Dave Grohl" and c["RoleName"] == "Composer"), None)
        assert match is not None
        assert match["OwnerIdentityID"] == 1

    def test_add_duplicate_is_idempotent(self, mutator, conn):
        # Song 6 already has Dave Grohl as Performer
        before = _get_credits(conn, 6)
        item = AddCreditItem.model_validate(
            {"type": "credit", "song_id": 6, "name": "Dave Grohl", "role": "Performer"}
        )
        mutator.apply_within("add", item, conn)
        conn.commit()
        after = _get_credits(conn, 6)
        assert len(after) == len(before)

    def test_unsupported_action_raises(self, mutator, conn):
        item = AddCreditItem.model_validate(
            {"type": "credit", "song_id": 7, "name": "X", "role": "Performer"}
        )
        with pytest.raises(ValueError):
            mutator.apply_within("bad_action", item, conn)


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

class TestCreditMutatorRemove:
    def test_remove_credit_deletes_link(self, mutator, conn):
        credit_id = _get_credit_id(conn, 6, "Dave Grohl", "Performer")
        item = RemoveCreditItem.model_validate(
            {"type": "credit", "song_id": 6, "id": credit_id}
        )
        mutator.apply_within("remove", item, conn)
        conn.commit()
        credits = _get_credits(conn, 6)
        assert not any(c["CreditID"] == credit_id for c in credits)

    def test_remove_keeps_other_credits(self, mutator, conn):
        credit_id = _get_credit_id(conn, 6, "Dave Grohl", "Performer")
        item = RemoveCreditItem.model_validate(
            {"type": "credit", "song_id": 6, "id": credit_id}
        )
        mutator.apply_within("remove", item, conn)
        conn.commit()
        credits = _get_credits(conn, 6)
        assert any(c["RoleName"] == "Composer" for c in credits)

    def test_remove_nonexistent_raises(self, mutator, conn):
        item = RemoveCreditItem.model_validate(
            {"type": "credit", "song_id": 6, "id": 99999}
        )
        with pytest.raises(LookupError):
            mutator.apply_within("remove", item, conn)


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestCreditMutatorUpdate:
    def test_update_display_name(self, mutator, conn):
        # NameID=10 is "Dave Grohl"
        item = UpdateCreditEntityItem.model_validate(
            {"type": "credit", "id": 10, "display_name": "Dave G."}
        )
        mutator.apply_within("update", item, conn)
        conn.commit()
        assert _get_display_name(conn, 10) == "Dave G."

    def test_update_affects_all_songs_with_name(self, mutator, conn):
        # NameID=10 appears on songs 6 and 8
        item = UpdateCreditEntityItem.model_validate(
            {"type": "credit", "id": 10, "display_name": "DG"}
        )
        mutator.apply_within("update", item, conn)
        conn.commit()
        for song_id in (6, 8):
            credits = _get_credits(conn, song_id)
            assert any(c["DisplayName"] == "DG" for c in credits)

    def test_update_null_display_name_is_noop(self, mutator, conn):
        original = _get_display_name(conn, 10)
        item = UpdateCreditEntityItem.model_validate({"type": "credit", "id": 10})
        mutator.apply_within("update", item, conn)
        conn.commit()
        assert _get_display_name(conn, 10) == original

    def test_update_unknown_name_id_raises(self, mutator, conn):
        item = UpdateCreditEntityItem.model_validate(
            {"type": "credit", "id": 99999, "display_name": "Ghost"}
        )
        with pytest.raises(LookupError):
            mutator.apply_within("update", item, conn)
