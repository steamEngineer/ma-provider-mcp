"""ASGI ↔ aiohttp bridge for mounting FastMCP under MA's webserver.

FastMCP v3 exposes a Starlette-based ASGI app for streamable-HTTP transport.
MA's main webserver is aiohttp. This bridge translates a single aiohttp
``web.Request`` into ASGI ``scope/receive/send`` events and back into a
``web.StreamResponse``, so we can mount the MCP app under any path that
``mass.webserver.register_dynamic_route`` accepts (we use ``/mcp/v1/*``).

Streaming responses (SSE / chunked) are passed through verbatim so MCP
keep-alive heartbeats and tool-progress events reach the client without
buffering.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from aiohttp import web

if TYPE_CHECKING:
    from collections.abc import Callable

    from music_assistant.mass import MusicAssistant

LOGGER = logging.getLogger(__name__)


_DEFAULT_PORTS = {"http": 80, "https": 443}


def _normalize_origin(origin: str) -> str | None:
    """Return ``scheme://host[:port]`` lower-cased, default-port stripped, or None.

    Rejects forms without scheme or netloc; preserves ``"null"`` verbatim so it
    can be matched against an explicit allowlist entry.
    """
    if not origin:
        return None
    if origin == "null":
        return "null"
    parts = urlsplit(origin)
    scheme = parts.scheme.lower()
    host = parts.hostname
    if not scheme or not host:
        return None
    port = parts.port
    if port is None or port == _DEFAULT_PORTS.get(scheme):
        return f"{scheme}://{host.lower()}"
    return f"{scheme}://{host.lower()}:{port}"


def _compute_origin_allowlist(
    mass: MusicAssistant, extra_origins_csv: str = ""
) -> frozenset[str]:
    """Build the set of accepted ``Origin`` values for the MCP endpoint.

    Always includes loopback variants (``http://localhost``, ``http://127.0.0.1``,
    ``http://[::1]``), the host derived from ``mass.webserver.base_url``, and the
    advertised ``mass.webserver.publish_ip``. Additional origins from config
    (CSV) are normalized and added.
    """
    allow: set[str] = {
        "http://localhost",
        "http://127.0.0.1",
        "http://[::1]",
    }

    base_url = str(getattr(mass.webserver, "base_url", "") or "")
    base_norm = _normalize_origin(base_url)
    if base_norm:
        allow.add(base_norm)
        # Same host on https is acceptable when MA is behind TLS-terminating proxy.
        if base_norm.startswith("http://"):
            allow.add("https://" + base_norm[len("http://") :])

    publish_ip = str(getattr(mass.webserver, "publish_ip", "") or "")
    if publish_ip:
        # Derive port from base_url; fallback: no port (browsers send port if non-default).
        port = _port_from_base_url(base_url)
        suffix = f":{port}" if port else ""
        allow.add(f"http://{publish_ip.lower()}{suffix}")
        allow.add(f"https://{publish_ip.lower()}{suffix}")

    for raw in (extra_origins_csv or "").split(","):
        norm = _normalize_origin(raw.strip())
        if norm:
            allow.add(norm)

    return frozenset(allow)


def _port_from_base_url(base_url: str) -> int | None:
    """Helper: return explicit port from a URL, or None if it's the scheme default."""
    if not base_url:
        return None
    parts = urlsplit(base_url)
    if parts.port is not None and parts.port != _DEFAULT_PORTS.get(parts.scheme.lower()):
        return parts.port
    return None


def _is_origin_allowed(origin: str | None, allowlist: frozenset[str]) -> bool:
    """Return True if the request's ``Origin`` should be accepted.

    Rules:

    * Missing ``Origin`` → allowed (stdio-style or non-browser MCP clients).
      Spec MUST applies to *present* Origin values.
    * ``Origin: null`` → allowed only if explicitly listed in the allowlist
      (some sandboxed iframes / file:// pages send it).
    * Any other value is normalized and matched literally.
    """
    if origin is None:
        return True
    norm = _normalize_origin(origin)
    if norm is None:
        return False
    return norm in allowlist


async def mount_into_mass(
    mass: MusicAssistant,
    mcp: Any,
    mount_path: str = "/mcp/v1",
) -> Callable[[], None]:
    """Register the FastMCP streamable-HTTP ASGI app under MA's webserver.

    :param mass: MusicAssistant instance.
    :param mcp: FastMCP server instance whose ``http_app`` is exposed.
    :param mount_path: Path prefix on the MA webserver (default ``/mcp/v1``).
    :return: Callable that, when invoked, unregisters the route.
    """
    asgi_app = _build_asgi_app(mcp)

    async def handler(request: web.Request) -> web.StreamResponse:
        return await _asgi_to_aiohttp(asgi_app, request, strip_prefix=mount_path)

    return mass.webserver.register_dynamic_route(f"{mount_path}/*", handler)


def _build_asgi_app(mcp: Any) -> Any:
    """Return the streamable-HTTP ASGI app from FastMCP, accommodating v3 minor renames."""
    if hasattr(mcp, "http_app"):
        return mcp.http_app(transport="streamable-http")
    if hasattr(mcp, "streamable_http_app"):
        return mcp.streamable_http_app()
    if hasattr(mcp, "asgi_app"):
        return mcp.asgi_app()
    msg = "Could not find an ASGI app factory on FastMCP instance"
    raise RuntimeError(msg)


async def _asgi_to_aiohttp(
    asgi_app: Any,
    request: web.Request,
    strip_prefix: str = "",
) -> web.StreamResponse:
    """Bridge a single aiohttp request through an ASGI app.

    The bridge supports streaming responses: ``http.response.body`` events
    with ``more_body=True`` are flushed to the client immediately, which is
    required for streamable-HTTP MCP transport.
    """
    scope = _build_scope(request, strip_prefix)
    body_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def receive() -> dict[str, Any]:
        return await body_queue.get()

    response_state: dict[str, Any] = {"started": False, "response": None, "disconnected": False}

    async def send(message: dict[str, Any]) -> None:
        msg_type = message.get("type")
        if msg_type == "http.response.start":
            status = int(message.get("status", 200))
            headers_list = message.get("headers", [])
            response = web.StreamResponse(status=status)
            for raw_name, raw_value in headers_list:
                name = raw_name.decode("latin-1") if isinstance(raw_name, bytes) else str(raw_name)
                value = (
                    raw_value.decode("latin-1") if isinstance(raw_value, bytes) else str(raw_value)
                )
                if name.lower() in {"transfer-encoding", "content-length"}:
                    continue
                response.headers[name] = value
            await response.prepare(request)
            response_state["response"] = response
            response_state["started"] = True
        elif msg_type == "http.response.body":
            response = response_state["response"]
            if response is None:
                msg = "ASGI app sent body before start"
                raise RuntimeError(msg)
            body = message.get("body", b"")
            if body:
                await response.write(body)
            if not message.get("more_body", False):
                await response.write_eof()

    async def pump_request_body() -> None:
        try:
            async for chunk in request.content.iter_chunked(64 * 1024):
                await body_queue.put({"type": "http.request", "body": chunk, "more_body": True})
            await body_queue.put({"type": "http.request", "body": b"", "more_body": False})
        except Exception:
            LOGGER.exception("MCP bridge: failed to pump request body")
            await body_queue.put({"type": "http.disconnect"})

    pump_task = asyncio.create_task(pump_request_body())
    try:
        await asgi_app(scope, receive, send)
    except Exception:
        LOGGER.exception("MCP bridge: ASGI app raised")
        if not response_state["started"]:
            return web.Response(status=500, text="Internal MCP bridge error")
        raise
    finally:
        pump_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await pump_task

    response = response_state["response"]
    if response is None:
        return web.Response(status=204)
    return response


def _build_scope(request: web.Request, strip_prefix: str) -> dict[str, Any]:
    """Convert an aiohttp request into a minimal ASGI HTTP scope dict."""
    raw_path = request.rel_url.raw_path
    if strip_prefix and raw_path.startswith(strip_prefix):
        raw_path = raw_path[len(strip_prefix) :]
    if not raw_path.startswith("/"):
        raw_path = "/" + raw_path

    headers: list[tuple[bytes, bytes]] = [
        (k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in request.headers.items()
    ]

    server_host = request.url.host or "localhost"
    server_port = request.url.port or (443 if request.url.scheme == "https" else 80)

    client_addr: tuple[str, int] | None = None
    peername = request.transport.get_extra_info("peername") if request.transport else None
    if peername and len(peername) >= 2:
        client_addr = (str(peername[0]), int(peername[1]))

    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": request.method,
        "scheme": request.url.scheme,
        "path": raw_path,
        "raw_path": raw_path.encode("latin-1"),
        "query_string": request.rel_url.raw_query_string.encode("latin-1"),
        "root_path": strip_prefix.rstrip("/"),
        "headers": headers,
        "server": (server_host, server_port),
        "client": client_addr,
    }
