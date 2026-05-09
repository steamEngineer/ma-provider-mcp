"""Token verifier delegating to MA's existing authentication subsystem.

The plugin does not implement JWT decoding or scope checks of its own — this
is intentional. ``mass.webserver.auth.authenticate_with_token`` already handles
both JWT (PR #2891) and legacy hash tokens, and updates the sliding-window
expiry on every successful call. Wiring our own JWT decode here would only
duplicate the work and create two sources of truth.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastmcp.server.auth import TokenVerifier
from mcp.server.auth.provider import AccessToken

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant

LOGGER = logging.getLogger(__name__)


class MASTokenVerifier(TokenVerifier):
    """Verify Bearer tokens against ``mass.webserver.auth``."""

    def __init__(self, mass: MusicAssistant) -> None:
        """Bind the verifier to a MusicAssistant instance.

        :param mass: MusicAssistant instance used to authenticate tokens.
        """
        super().__init__()
        self._mass = mass

    async def verify_token(self, token: str) -> AccessToken | None:
        """Validate the bearer token and produce an ``AccessToken`` for FastMCP.

        :param token: Raw bearer token from the ``Authorization`` header.
        :return: ``AccessToken`` if the token is valid and the user is enabled,
            otherwise ``None``.
        """
        try:
            user = await self._mass.webserver.auth.authenticate_with_token(token)
        except Exception:
            LOGGER.exception("MA token verification raised")
            return None

        if user is None or not getattr(user, "enabled", True):
            return None

        role_value = getattr(getattr(user, "role", None), "value", "user")

        return AccessToken(
            token=token,
            client_id=str(getattr(user, "user_id", "")) or "music-assistant",
            scopes=[str(role_value)],
            expires_at=None,
            resource=None,
            claims={
                "username": getattr(user, "username", ""),
                "role": str(role_value),
            },
        )
