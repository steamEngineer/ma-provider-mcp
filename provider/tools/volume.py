"""Volume control: set, up/down, mute, group volume."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import FastMCP

from ..tags import Tag

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant


def build_volume_server(mass: MusicAssistant) -> FastMCP:
    """Construct the ``volume/*`` sub-server."""
    sub: FastMCP = FastMCP(name="volume")

    @sub.tool(tags={Tag.CONTROL_VOLUME})
    async def volume_set(player_id: str, level: int) -> None:
        """Set absolute volume level (0-100) on a player."""
        await mass.players.cmd_volume_set(player_id, max(0, min(100, int(level))))

    @sub.tool(tags={Tag.CONTROL_VOLUME})
    async def volume_up(player_id: str) -> None:
        """Bump volume up one step."""
        await mass.players.cmd_volume_up(player_id)

    @sub.tool(tags={Tag.CONTROL_VOLUME})
    async def volume_down(player_id: str) -> None:
        """Bump volume down one step."""
        await mass.players.cmd_volume_down(player_id)

    @sub.tool(tags={Tag.CONTROL_VOLUME})
    async def volume_mute(player_id: str, muted: bool) -> None:
        """Mute or unmute a player."""
        await mass.players.cmd_volume_mute(player_id, muted)

    @sub.tool(tags={Tag.CONTROL_VOLUME})
    async def group_volume_set(player_id: str, level: int) -> None:
        """Set group volume level (0-100) on a sync group."""
        await mass.players.cmd_group_volume(player_id, max(0, min(100, int(level))))

    return sub
