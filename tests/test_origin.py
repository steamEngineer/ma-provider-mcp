"""Tests for Origin allowlist computation and matching (C1)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from provider.http_bridge import (
    _compute_origin_allowlist,
    _is_origin_allowed,
    _normalize_origin,
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
