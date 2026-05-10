"""ACTION-handler: mints a bootstrap token and signals the wizard URL to the frontend.

Triggered by the ``open_connect`` ``ConfigEntryType.ACTION`` button defined in
:mod:`provider.config`. Mirrors the Spotify-provider OAuth pattern (signal an
``EventType.AUTH_SESSION`` event whose ``data`` is the URL the MA frontend
should ``window.open``).
"""

from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant

LOGGER = logging.getLogger(__name__)


async def handle_open_connect_action(
    mass: MusicAssistant,
    *,
    current_user: Any,
    mount_path: str,
    base_url: str,
) -> None:
    """Open the Connect Wizard in the user's browser via MA's auth-session signal.

    :param mass: MusicAssistant instance.
    :param current_user: The authenticated MA ``User`` invoking the action, or
        ``None`` when no user context is available — in which case the wizard
        is opened without a bootstrap token and falls back to its login form.
    :param mount_path: HTTP path prefix where the MCP server is mounted.
    :param base_url: Public base URL of MA (no trailing slash).
    """
    bootstrap: str | None = None
    if current_user is not None:
        try:
            bootstrap = await mass.webserver.auth.create_token(
                user=current_user,
                name="MCP — wizard bootstrap",
                is_long_lived=False,
            )
        except Exception:
            LOGGER.exception("Connect Wizard: failed to mint bootstrap token")
            bootstrap = None

    base = base_url.rstrip("/")
    mount = "/" + mount_path.strip("/")
    url = f"{base}{mount}/connect"
    if bootstrap:
        url = f"{url}?{urlencode({'bootstrap': bootstrap})}"

    session_id = f"mcp-connect-{secrets.token_urlsafe(8)}"
    _signal_auth_session(mass, session_id=session_id, url=url)


def _signal_auth_session(mass: MusicAssistant, *, session_id: str, url: str) -> None:
    """Publish the wizard URL via MA's ``EventType.AUTH_SESSION`` signal.

    The MA frontend subscribes to ``AUTH_SESSION`` events and ``window.open``-s
    the carried URL — same mechanism the Spotify, Audible, QQMusic providers
    use for OAuth redirect. Never raises: if the event bus rejects the call we
    log and degrade gracefully (the wizard URL is still in the logs).
    """
    from music_assistant_models.enums import EventType  # noqa: PLC0415

    try:
        mass.signal_event(EventType.AUTH_SESSION, object_id=session_id, data=url)
    except Exception:
        LOGGER.exception("Connect Wizard: signal_event failed")
