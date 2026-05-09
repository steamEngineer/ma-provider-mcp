"""MCPServerRuntime — composes FastMCP, mounts it into MA's webserver."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .constants import (
    CONF_MOUNT_PATH,
    CONF_REQUIRE_AUTH,
    DEFAULT_MOUNT_PATH,
)
from .tags import enabled_tags

if TYPE_CHECKING:
    from collections.abc import Callable

    from music_assistant_models.config_entries import ProviderConfig

    from music_assistant.mass import MusicAssistant

LOGGER = logging.getLogger(__name__)


class MCPServerRuntime:
    """Build and manage a FastMCP server mounted into MA's webserver.

    The lifecycle is intentionally simple:

    * :meth:`start` builds the FastMCP root, mounts namespaced sub-servers
      for each tool category, registers resources and prompts, applies the
      tag-filter middleware, and exposes the streamable-HTTP ASGI app on
      MA's webserver under :pyattr:`mount_path`.
    * :meth:`stop` unregisters the dynamic route.
    * :meth:`apply_permission_change` rebuilds the runtime in place when
      only permission flags / resource toggles changed (no port collision
      since we reuse MA's webserver).
    """

    def __init__(
        self,
        mass: MusicAssistant,
        config: ProviderConfig,
        logger: logging.Logger,
    ) -> None:
        """Hold the shared dependencies; nothing is started here.

        :param mass: MusicAssistant instance.
        :param config: Provider config.
        :param logger: Provider-scoped logger.
        """
        self._mass = mass
        self._config = config
        self._logger = logger
        self._mount_path: str = str(config.get_value(CONF_MOUNT_PATH) or DEFAULT_MOUNT_PATH)
        self._mcp: Any = None
        self._unmount: Callable[[], None] | None = None

    @property
    def public_url(self) -> str:
        """Return the externally visible MCP endpoint URL."""
        base = str(getattr(self._mass.webserver, "base_url", "")).rstrip("/")
        return f"{base}{self._mount_path}"

    async def start(self) -> None:
        """Build the FastMCP server and mount it into the MA webserver."""
        from fastmcp import FastMCP  # noqa: PLC0415

        from .auth import MASTokenVerifier  # noqa: PLC0415
        from .http_bridge import mount_into_mass  # noqa: PLC0415
        from .prompts import register_prompts  # noqa: PLC0415
        from .resources import register_resources  # noqa: PLC0415
        from .tools import (  # noqa: PLC0415
            build_library_server,
            build_media_server,
            build_metadata_server,
            build_playback_server,
            build_players_server,
            build_playlists_server,
            build_queue_server,
            build_volume_server,
        )

        require_auth = bool(self._config.get_value(CONF_REQUIRE_AUTH))
        verifier = MASTokenVerifier(self._mass) if require_auth else None

        mcp = FastMCP(
            name="music-assistant",
            instructions=(
                "Music Assistant MCP server: control playback, browse the library, "
                "manage queues, and inspect players. Tools are namespaced by category "
                "(library_, queue_, playback_, players_, playlists_, volume_, media_, "
                "metadata_). Resources expose URI-addressable views: library://artist/{id}, "
                "library://album/{id}, library://track/{id}, library://playlist/{id}, "
                "player://{id}, queue://{id}."
            ),
            auth=verifier,
        )

        mcp.mount(build_library_server(self._mass), namespace="library")
        mcp.mount(build_queue_server(self._mass), namespace="queue")
        mcp.mount(build_playback_server(self._mass), namespace="playback")
        mcp.mount(build_players_server(self._mass), namespace="players")
        mcp.mount(build_playlists_server(self._mass), namespace="playlists")
        mcp.mount(build_volume_server(self._mass), namespace="volume")
        mcp.mount(build_media_server(self._mass), namespace="media")
        mcp.mount(build_metadata_server(self._mass), namespace="metadata")

        register_resources(mcp, self._mass, self._config)
        register_prompts(mcp, self._mass, self._config)

        self._apply_tag_filter(mcp, enabled_tags(self._config))

        self._mcp = mcp
        self._unmount = await mount_into_mass(self._mass, mcp, self._mount_path)
        self._logger.debug(
            "MCP runtime started: mount=%s, auth=%s, tags=%d",
            self._mount_path,
            bool(verifier),
            len(enabled_tags(self._config)),
        )

    async def stop(self) -> None:
        """Unregister the HTTP route and drop references."""
        if self._unmount is not None:
            try:
                self._unmount()
            except Exception:
                self._logger.exception("Failed to unregister MCP route")
            self._unmount = None
        self._mcp = None

    async def apply_permission_change(self, new_config: ProviderConfig) -> None:
        """Hot-swap the allowed-tag set without rebuilding FastMCP / remounting.

        Resource toggles (``CONF_RES_*``) require a rebuild because resource
        registration is decided at ``register_resources`` time; permission flags
        flip the tag set in the closure read by :class:`TagFilterMiddleware` and
        take effect on the next request.
        """
        from .constants import PERMISSION_KEYS  # noqa: PLC0415

        permission_only = {
            key for key in self._diff_keys(self._config, new_config) if key in PERMISSION_KEYS
        } == set(self._diff_keys(self._config, new_config))

        self._config = new_config
        if permission_only and hasattr(self, "_allowed_tags"):
            self._allowed_tags = {str(t) for t in enabled_tags(new_config)}
            self._logger.debug(
                "MCP runtime: hot-swapped tag filter to %d tags",
                len(self._allowed_tags),
            )
            return

        await self.stop()
        await self.start()

    @staticmethod
    def _diff_keys(old: ProviderConfig, new: ProviderConfig) -> set[str]:
        """Return the set of config keys whose values differ between two configs."""
        try:
            old_values = old.values if hasattr(old, "values") else {}
            new_values = new.values if hasattr(new, "values") else {}
        except Exception:
            return set()
        keys = set(old_values) | set(new_values)
        return {k for k in keys if old_values.get(k) != new_values.get(k)}

    def _apply_tag_filter(self, mcp: Any, allowed: set[Any]) -> None:
        """Install the tag-filter middleware on the given FastMCP server."""
        from .middleware import TagFilterMiddleware  # noqa: PLC0415

        # Snapshot tags into a tuple captured by the closure below. The closure
        # form lets us swap the allowed set later via apply_permission_change
        # without re-instantiating the middleware (single source of truth).
        self._allowed_tags: set[str] = {str(t) for t in allowed}
        mcp.add_middleware(TagFilterMiddleware(lambda: self._allowed_tags))
