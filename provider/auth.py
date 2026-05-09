"""Token verifier delegating to MA's existing authentication subsystem.

The plugin does not implement JWT decoding or scope checks of its own — this
is intentional. ``mass.webserver.auth.authenticate_with_token`` already handles
both JWT (PR #2891) and legacy hash tokens, and updates the sliding-window
expiry on every successful call. Wiring our own JWT decode here would only
duplicate the work and create two sources of truth.

Passing ``base_url`` upstream to :class:`fastmcp.server.auth.TokenVerifier`
lets FastMCP's built-in ``RequireAuthMiddleware`` populate the
``resource_metadata="…"`` parameter in ``WWW-Authenticate`` headers on
401 responses (RFC 9728 / MCP authorization spec MUST).
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

    def __init__(
        self,
        mass: MusicAssistant,
        *,
        base_url: str | None = None,
        public_resource_uri: str | None = None,
    ) -> None:
        """Bind the verifier to a MusicAssistant instance.

        :param mass: MusicAssistant instance used to authenticate tokens.
        :param base_url: Public base URL of this MA instance (used by FastMCP
            to build the ``resource_metadata`` URL advertised in 401 responses
            and the ``aud`` claim binding).
        :param public_resource_uri: Canonical URI of the MCP server (the value
            FastMCP will report as ``resource``). Used to populate
            ``AccessToken.resource`` so downstream code can audience-check.
        """
        super().__init__(base_url=base_url) if base_url else super().__init__()
        self._mass = mass
        self._public_resource_uri = public_resource_uri

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

        # MCP SDK's AccessToken pydantic model has no `claims` field — extras
        # are silently dropped — so we don't try to forward username/role here.
        return AccessToken(
            token=token,
            client_id=str(getattr(user, "user_id", "")) or "music-assistant",
            scopes=[],
            expires_at=None,
            resource=self._public_resource_uri,
        )
