"""Tests for Origin allowlist computation, matching, and bridge enforcement (C1+C2)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from provider.http_bridge import (
    _compute_origin_allowlist,
    _is_origin_allowed,
    _normalize_origin,
    mount_into_mass,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://localhost:8095", "http://localhost:8095"),
        ("HTTP://Localhost:8095", "http://localhost:8095"),
        ("http://localhost:80", "http://localhost"),
        ("https://example.com:443", "https://example.com"),
        ("https://example.com/path", "https://example.com"),
        ("null", "null"),
        ("", None),
        ("not-a-url", None),
        ("http://", None),
    ],
)
def test_normalize_origin(raw: str, expected: str | None) -> None:
    """Origin strings collapse to ``scheme://host[:port]`` lowercased, default ports stripped."""
    assert _normalize_origin(raw) == expected


def _fake_mass(base_url: str = "http://localhost:8095", publish_ip: str = "127.0.0.1"):
    return SimpleNamespace(
        webserver=SimpleNamespace(base_url=base_url, publish_ip=publish_ip)
    )


def test_compute_allowlist_default() -> None:
    """Default allowlist contains loopbacks, base_url host, and publish_ip."""
    allow = _compute_origin_allowlist(_fake_mass())
    # loopbacks always there
    assert "http://localhost" in allow
    assert "http://127.0.0.1" in allow
    assert "http://[::1]" in allow
    # base_url with port
    assert "http://localhost:8095" in allow
    # https-twin of base_url
    assert "https://localhost:8095" in allow
    # publish_ip with derived port
    assert "http://127.0.0.1:8095" in allow
    assert "https://127.0.0.1:8095" in allow


def test_compute_allowlist_with_extras() -> None:
    """CSV ``extra_origins`` get normalized; bogus / empty entries silently dropped."""
    allow = _compute_origin_allowlist(
        _fake_mass(),
        extra_origins_csv="https://ha.example.com, http://reverse.lan:8443 ,bogus,",
    )
    assert "https://ha.example.com" in allow
    assert "http://reverse.lan:8443" in allow
    # bogus + empty silently dropped
    assert all(o != "" for o in allow)


def test_compute_allowlist_with_https_base_url() -> None:
    """When base_url uses https on the default port, no port suffix is added."""
    allow = _compute_origin_allowlist(_fake_mass(base_url="https://mcp.example.com"))
    assert "https://mcp.example.com" in allow
    # publish_ip with no explicit port (https is scheme-default)
    assert "http://127.0.0.1" in allow
    assert "https://127.0.0.1" in allow


def test_compute_allowlist_handles_missing_attrs() -> None:
    """If ``mass.webserver`` lacks base_url/publish_ip, only loopbacks remain."""
    mass = SimpleNamespace(webserver=SimpleNamespace())
    allow = _compute_origin_allowlist(mass)
    assert "http://localhost" in allow
    assert "http://127.0.0.1" in allow


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [
        (None, True),  # CLI / stdio-style — no Origin
        ("http://localhost:8095", True),
        ("http://LOCALHOST:8095", True),  # case-insensitive
        ("http://localhost:8095/", True),  # trailing slash tolerated
        ("http://evil.example", False),
        ("https://localhost:8095", True),  # https-twin allowed by default
        ("null", False),  # not in default allowlist
    ],
)
def test_is_origin_allowed(origin: str | None, allowed: bool) -> None:
    """Match Origin against the default allowlist (case-insensitive, trailing-slash tolerant)."""
    allow = _compute_origin_allowlist(_fake_mass())
    assert _is_origin_allowed(origin, allow) is allowed


def test_is_origin_allowed_with_explicit_null() -> None:
    """``Origin: null`` is accepted only when the operator opts in via ``extra_origins``."""
    allow = _compute_origin_allowlist(_fake_mass(), extra_origins_csv="null")
    assert "null" in allow
    assert _is_origin_allowed("null", allow) is True


def test_garbage_origin_rejected() -> None:
    """Malformed Origin values fail closed with 403."""
    allow = _compute_origin_allowlist(_fake_mass())
    assert _is_origin_allowed("not-a-url", allow) is False
    assert _is_origin_allowed("http://", allow) is False


# ── End-to-end bridge enforcement (C2) ──────────────────────────────────────


class _FakeMcp:
    """Stand-in for FastMCP exposing an ASGI app via ``http_app(...)``."""

    def __init__(self, asgi_app: Any) -> None:
        self._app = asgi_app

    def http_app(self, transport: str = "streamable-http") -> Any:
        return self._app


async def _echo_asgi(scope: dict, receive: Any, send: Any) -> None:  # noqa: ARG001
    """Minimal ASGI app that returns 200 with body 'OK'."""
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"OK"})


class _FakeWebserver:
    """Captures the dynamic-route handler so a TestClient can hit it directly."""

    def __init__(self) -> None:
        self.handler: Any = None
        self.path: str | None = None
        self.base_url = "http://localhost:8095"
        self.publish_ip = "127.0.0.1"

    def register_dynamic_route(self, path: str, handler: Any, method: str = "*") -> Any:
        self.path = path
        self.handler = handler
        return lambda: None


@pytest.fixture
async def bridge_client(extra_origins: str = "") -> Any:  # noqa: ARG001
    """Fixture: build the bridge handler against a fake MA + fake ASGI, expose via TestClient."""
    fake_ws = _FakeWebserver()
    mass = SimpleNamespace(webserver=fake_ws)
    mcp = _FakeMcp(_echo_asgi)
    await mount_into_mass(mass, mcp, mount_path="/mcp/v1", extra_origins_csv="")

    app = web.Application()
    app.router.add_route("*", "/mcp/v1/{tail:.*}", fake_ws.handler)
    async with TestClient(TestServer(app)) as client:
        yield client


async def test_bridge_rejects_evil_origin(bridge_client: TestClient) -> None:
    """A non-allow-listed Origin is blocked with 403, ASGI never invoked."""
    resp = await bridge_client.post(
        "/mcp/v1/", headers={"Origin": "http://evil.example"}
    )
    assert resp.status == 403


async def test_bridge_allows_localhost(bridge_client: TestClient) -> None:
    """Origin that matches base_url is forwarded to ASGI (200 from echo app)."""
    resp = await bridge_client.post(
        "/mcp/v1/", headers={"Origin": "http://localhost:8095"}
    )
    assert resp.status == 200
    assert (await resp.read()) == b"OK"


async def test_bridge_allows_no_origin(bridge_client: TestClient) -> None:
    """Requests without ``Origin`` header (curl/CLI) pass through unchanged."""
    resp = await bridge_client.post("/mcp/v1/")
    assert resp.status == 200


async def test_bridge_with_extra_origins() -> None:
    """``extra_origins_csv`` widens the allowlist for reverse-proxy / HA ingress."""
    fake_ws = _FakeWebserver()
    mass = SimpleNamespace(webserver=fake_ws)
    mcp = _FakeMcp(_echo_asgi)
    await mount_into_mass(
        mass, mcp, mount_path="/mcp/v1", extra_origins_csv="https://ha.example.com"
    )

    app = web.Application()
    app.router.add_route("*", "/mcp/v1/{tail:.*}", fake_ws.handler)
    async with TestClient(TestServer(app)) as client:
        resp = await client.post(
            "/mcp/v1/", headers={"Origin": "https://ha.example.com"}
        )
        assert resp.status == 200
        # An origin not in the extras stays rejected.
        resp = await client.post(
            "/mcp/v1/", headers={"Origin": "http://evil.example"}
        )
        assert resp.status == 403
