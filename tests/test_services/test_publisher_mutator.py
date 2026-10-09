"""
Tests for PublisherMutator — entity update guards.

Uses populated_db. Publishers: 1 Universal Music Group, 4 Roswell Records, 5 Sub Pop.
"""

import sqlite3

import pytest

from src.engine.routers.mutation_models import UpdatePublisherEntityItem
from src.services.mutators.publisher_mutator import PublisherMutator


def _make_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.create_collation(
        "UTF8_NOCASE",
        lambda s1, s2: (s1.lower() > s2.lower()) - (s1.lower() < s2.lower()),
    )
    return conn


def _get_name(conn: sqlite3.Connection, publisher_id: int) -> str:
    row = conn.execute(
        "SELECT PublisherName FROM Publishers WHERE PublisherID = ?", (publisher_id,)
    ).fetchone()
    assert row is not None
    return row["PublisherName"]


@pytest.fixture
def mutator(populated_db):
    return PublisherMutator(populated_db)


@pytest.fixture
def conn(populated_db):
    c = _make_conn(populated_db)
    yield c
    c.close()


class TestPublisherMutatorUpdate:
    def test_update_name(self, mutator, conn):
        item = UpdatePublisherEntityItem.model_validate(
            {"type": "publisher", "id": 4, "name": "Roswell"}
        )
        mutator.apply_within("update", item, conn)
        conn.commit()
        assert _get_name(conn, 4) == "Roswell"

    def test_update_soft_deleted_colliding_raises_lookup_not_merge(self, mutator, conn):
        # A publisher merged away is soft-deleted. A stale rename onto a live name
        # must 404, not raise MergeRequired.
        conn.execute("UPDATE Publishers SET IsDeleted = 1 WHERE PublisherID = 4")
        item = UpdatePublisherEntityItem.model_validate(
            {"type": "publisher", "id": 4, "name": "Sub Pop"}
        )
        with pytest.raises(LookupError):
            mutator.apply_within("update", item, conn)

    def test_update_soft_deleted_does_not_rename_it(self, mutator, conn):
        conn.execute("UPDATE Publishers SET IsDeleted = 1 WHERE PublisherID = 4")
        item = UpdatePublisherEntityItem.model_validate(
            {"type": "publisher", "id": 4, "name": "Brand New Label"}
        )
        with pytest.raises(LookupError):
            mutator.apply_within("update", item, conn)
        assert _get_name(conn, 4) == "Roswell Records"
