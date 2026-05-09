"""Media: favorites, library add/remove, announcements."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from ..tags import Tag
from ._common import TIMEOUT_MUTATION, confirm_or_raise

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant


def build_media_server(
    mass: MusicAssistant, *, require_confirmation: bool = True
) -> FastMCP:
    """Construct the ``media/*`` sub-server."""
    sub: FastMCP = FastMCP(name="media")

    @sub.tool(
        tags={Tag.EDIT_FAVORITES},
        annotations=ToolAnnotations(
            title="Add to favorites",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        timeout=TIMEOUT_MUTATION,
    )
    async def add_to_favorites(uri: str) -> None:
        """Add a media item (by URI) to favorites."""
        await mass.music.add_item_to_favorites(uri)

    @sub.tool(
        tags={Tag.DELETE_FAVORITES},
        annotations=ToolAnnotations(
            title="Remove from favorites",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        timeout=TIMEOUT_MUTATION,
    )
    async def remove_from_favorites(uri: str, ctx: Context | None = None) -> None:
        """Remove a media item (by URI) from favorites."""
        await confirm_or_raise(
            ctx,
            f"Remove {uri!r} from favorites?",
            enabled=require_confirmation,
        )
        await mass.music.remove_item_from_favorites(uri)

    @sub.tool(
        tags={Tag.EDIT_LIBRARY},
        annotations=ToolAnnotations(
            title="Add to library",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        timeout=TIMEOUT_MUTATION,
    )
    async def add_to_library(uri: str) -> None:
        """Add a media item (by URI) to the library."""
        await mass.music.add_item_to_library(uri)

    @sub.tool(
        tags={Tag.DELETE_LIBRARY},
        annotations=ToolAnnotations(
            title="Remove from library",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        timeout=TIMEOUT_MUTATION,
    )
    async def remove_from_library(uri: str, ctx: Context | None = None) -> None:
        """Remove a media item (by URI) from the library."""
        await confirm_or_raise(
            ctx,
            f"Remove {uri!r} from the library? This cannot be undone.",
            enabled=require_confirmation,
        )
        await mass.music.remove_item_from_library(uri)

    @sub.tool(
        tags={Tag.CONTROL_MEDIA},
        annotations=ToolAnnotations(
            title="Mark item played",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
        timeout=TIMEOUT_MUTATION,
    )
    async def mark_played(uri: str) -> None:
        """Mark a media item as played (updates play history)."""
        await mass.music.mark_item_played(uri)

    @sub.tool(
        tags={Tag.CONTROL_MEDIA},
        annotations=ToolAnnotations(
            title="Play announcement",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
        timeout=TIMEOUT_MUTATION,
    )
    async def play_announcement(player_id: str, url: str, volume_level: int | None = None) -> None:
        """Play a one-shot announcement audio URL on a player."""
        await mass.players.play_announcement(player_id, url, volume_level=volume_level)

    return sub
