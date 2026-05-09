"""Playlists: create, modify, delete."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..models import PlaylistBrief
from ..tags import Tag
from ._common import to_brief_playlist

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant


def build_playlists_server(mass: MusicAssistant) -> FastMCP:
    """Construct the ``playlists/*`` sub-server."""
    sub: FastMCP = FastMCP(name="playlists")

    @sub.tool(
        tags={Tag.EDIT_PLAYLISTS},
        annotations=ToolAnnotations(
            title="Create a playlist",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def create_playlist(name: str, provider_instance_id: str | None = None) -> PlaylistBrief:
        """Create a new playlist on a music provider."""
        playlist = await mass.music.playlists.create_playlist(
            name, provider_instance_id_or_domain=provider_instance_id
        )
        return to_brief_playlist(playlist)

    @sub.tool(
        tags={Tag.EDIT_PLAYLISTS},
        annotations=ToolAnnotations(
            title="Add a single track to a playlist",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def add_track(playlist_id: str | int, track_uri: str) -> None:
        """Append one track to a playlist."""
        await mass.music.playlists.add_playlist_track(playlist_id, track_uri)

    @sub.tool(
        tags={Tag.EDIT_PLAYLISTS},
        annotations=ToolAnnotations(
            title="Add tracks to a playlist",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def add_tracks(playlist_id: str | int, track_uris: list[str]) -> None:
        """Append multiple tracks to a playlist."""
        await mass.music.playlists.add_playlist_tracks(playlist_id, track_uris)

    @sub.tool(
        tags={Tag.DELETE_PLAYLISTS},
        annotations=ToolAnnotations(
            title="Remove tracks from a playlist",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def remove_tracks(
        playlist_id: str | int,
        positions: list[int],
    ) -> None:
        """Remove tracks at the given zero-based positions from a playlist."""
        await mass.music.playlists.remove_playlist_tracks(playlist_id, positions)

    return sub
