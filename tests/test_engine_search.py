import os
import asyncio
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from src.engine_server import get_dashboard
from src.engine.routers.catalog import search_songs


def test_engine_search_songs_logic(populated_db):
    """Verify the search_songs endpoint logic directly."""
    os.environ["GOSLING_DB_PATH"] = populated_db

    # Run the async router function manually
    results = asyncio.run(search_songs(q="Everlong"))

    assert len(results) >= 1
    assert results[0].title == "Everlong"
    assert len(results[0].credits) >= 1


def test_dashboard_serving_logic():
    """Verify the dashboard serving logic directly."""
    response = asyncio.run(get_dashboard())
    assert "GOSLING" in response
    assert "<!DOCTYPE html>" in response


def test_engine_search_allows_short_query(populated_db):
    """Verify that the engine now allows single character queries for exploration."""
    os.environ["GOSLING_DB_PATH"] = populated_db
    results = asyncio.run(search_songs(q="E"))
    assert isinstance(results, list)


def test_dashboard_serving_missing_file():
    """Verify 404 handling when dashboard template is missing."""
    # Must patch where it is USED: src.engine_server.os.path.exists
    with patch("src.engine_server.os.path.exists", return_value=False):
        with pytest.raises(HTTPException) as excinfo:
            asyncio.run(get_dashboard())
        assert excinfo.value.status_code == 404
        assert "Dashboard UI template not found" in str(excinfo.value.detail)
