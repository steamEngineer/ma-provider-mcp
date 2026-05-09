"""Players: list, inspect, power, group."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import FastMCP

from ..models import PlayerBrief
from ..tags import Tag
from ._common import to_brief_player

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant


def build_players_server(mass: MusicAssistant) -> FastMCP:
    """Construct the ``players/*`` sub-server."""
    sub: FastMCP = FastMCP(name="players")

    @sub.tool(tags={Tag.QUERY_PLAYERS})
    async def list_players() -> list[PlayerBrief]:
        """List all players known to MA."""
        all_players = mass.players.all_players() if hasattr(mass.players, "all_players") else []
        if callable(all_players):
            all_players = all_players()
        return [to_brief_player(p) for p in all_players]

    @sub.tool(tags={Tag.QUERY_PLAYERS})
    async def get_player(player_id: str) -> PlayerBrief | None:
        """Return a single player by id, or ``None`` if it doesn't exist."""
        player = mass.players.get(player_id) if hasattr(mass.players, "get") else None
        return to_brief_player(player) if player is not None else None

    @sub.tool(tags={Tag.CONTROL_PLAYERS})
    async def set_power(player_id: str, powered: bool) -> None:
        """Power a player on or off."""
        await mass.players.cmd_power(player_id, powered)

    @sub.tool(tags={Tag.CONTROL_PLAYERS})
    async def group_player(player_id: str, target_player_id: str) -> None:
        """Group ``player_id`` with ``target_player_id`` (sync group)."""
        await mass.players.cmd_group(player_id, target_player_id)

    return sub
