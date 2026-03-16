import pytest
import httpx

from app.core.config import settings
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    )


def _headers() -> dict[str, str]:
    return {"X-API-Key": settings.api_key}


def _start_payload() -> dict:
    return {
        "target_domain": "https://example.com",
        "my_product_usp": "Fast onboarding with built-in automation",
        "ideal_customer_profile": "SMB teams needing simple growth workflows",
    }


@pytest.mark.asyncio
async def test_versioned_route_available(client):
    async with client as c:
        r = await c.get("/v1/input_schema")
    assert r.status_code == 200
    assert "Warning" not in r.headers


@pytest.mark.asyncio
async def test_legacy_route_warns(client):
    async with client as c:
        r = await c.get("/input_schema")
    assert r.status_code == 200
    assert "Deprecated route" in r.headers.get("Warning", "")


@pytest.mark.asyncio
async def test_error_includes_request_id(client):
    async with client as c:
        r = await c.post("/v1/start_job", json=_start_payload())
    assert r.status_code == 401
    body = r.json()
    assert "request_id" in body


@pytest.mark.asyncio
async def test_success_response_has_request_id_header(client):
    async with client as c:
        r = await c.post("/v1/start_job", json=_start_payload(), headers=_headers())
    assert r.status_code == 201
    assert "X-Request-ID" in r.headers


@pytest.mark.asyncio
async def test_availability_degraded_details(client, app, monkeypatch):
    async def _down() -> bool:
        return False

    monkeypatch.setattr(app.state.normaliser, "health_check", _down)
    async with client as c:
        r = await c.get("/v1/availability")

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert body["details"]["openrouter"] is False
