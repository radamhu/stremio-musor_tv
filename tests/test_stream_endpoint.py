"""Tests for stream endpoint functionality."""
import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_stream_endpoint_exists():
    """Test that the stream endpoint exists and returns 200."""
    response = client.get("/stream/movie/musortv:rtl:1234567890:test.json")
    assert response.status_code == 200


def test_stream_endpoint_returns_empty_streams():
    """Test that the stream endpoint returns empty streams array."""
    response = client.get("/stream/movie/musortv:rtl:1234567890:test.json")
    data = response.json()
    assert "streams" in data
    assert data["streams"] == []


def test_stream_endpoint_validates_id_format():
    """Test that invalid ID format still returns empty streams (not error)."""
    response = client.get("/stream/movie/invalid-id-format.json")
    assert response.status_code == 200
    data = response.json()
    assert data["streams"] == []


def test_stream_endpoint_with_valid_musortv_id():
    """Test stream endpoint with properly formatted musor.tv ID."""
    # Format: musortv:channel:timestamp:title-slug
    valid_id = "musortv:rtl:1729372800:matrix"
    response = client.get(f"/stream/movie/{valid_id}.json")
    assert response.status_code == 200
    data = response.json()
    assert data["streams"] == []


def test_manifest_includes_stream_resource():
    """Test that the manifest declares stream resource."""
    response = client.get("/manifest.json")
    assert response.status_code == 200
    manifest = response.json()
    assert "resources" in manifest
    assert "catalog" in manifest["resources"]
    assert "stream" in manifest["resources"]


def test_stream_endpoint_different_types():
    """Test stream endpoint with different content types."""
    # Movie
    response = client.get("/stream/movie/musortv:rtl:1234567890:test.json")
    assert response.status_code == 200
    assert response.json()["streams"] == []
    
    # Series (even though we don't use it, endpoint should handle it)
    response = client.get("/stream/series/musortv:rtl:1234567890:test.json")
    assert response.status_code == 200
    assert response.json()["streams"] == []


def test_stream_response_content_type():
    """Test that stream endpoint returns JSON content type."""
    response = client.get("/stream/movie/musortv:rtl:1234567890:test.json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_stream_endpoint_logs_request(caplog):
    """Test that stream requests are logged for debugging."""
    import logging
    caplog.set_level(logging.INFO)
    
    response = client.get("/stream/movie/musortv:rtl:1234567890:test.json")
    assert response.status_code == 200
    
    # Check that the request was logged
    log_messages = [record.message for record in caplog.records]
    assert any("Stream request" in msg for msg in log_messages)
