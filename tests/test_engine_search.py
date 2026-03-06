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
    assert "GOSLING V3CORE" in response
    assert "<!DOCTYPE html>" in response


def test_engine_search_guard_violates_short_query():
    """Verify that the engine as gatekeeper raises 400 for short queries."""
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(search_songs(q="E"))
    assert excinfo.value.status_code == 400
    assert "at least 2 characters" in str(excinfo.value.detail)


def test_dashboard_serving_missing_file():
    """Verify 404 handling when dashboard template is missing."""
    # Must patch where it is USED: src.engine_server.os.path.exists
    with patch("src.engine_server.os.path.exists", return_value=False):
        with pytest.raises(HTTPException) as excinfo:
            asyncio.run(get_dashboard())
        assert excinfo.value.status_code == 404
        assert "Dashboard UI template not found" in str(excinfo.value.detail)
