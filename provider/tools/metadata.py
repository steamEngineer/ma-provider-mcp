"""Metadata: lyrics, recommendations, similar tracks, refresh."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from ..models import TrackBrief
from ..tags import Tag
from ._common import to_brief_track

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant


def build_metadata_server(mass: MusicAssistant) -> FastMCP:
    """Construct the ``metadata/*`` sub-server."""
    sub: FastMCP = FastMCP(name="metadata")

    @sub.tool(tags={Tag.QUERY_METADATA})
    async def recommendations() -> list[dict[str, Any]]:
        """Return Music Assistant's curated recommendations folders."""
        folders = await mass.music.recommendations()
        result: list[dict[str, Any]] = []
        for folder in folders:
            folder_items = getattr(folder, "items", None) or []
            result.append(
                {
                    "name": getattr(folder, "name", ""),
                    "items": [str(getattr(it, "uri", "")) for it in folder_items],
                }
            )
        return result

    @sub.tool(tags={Tag.QUERY_METADATA})
    async def recently_played(limit: int = 10) -> list[TrackBrief]:
        """Return the user's recently played tracks."""
        items = await mass.music.recently_played(limit=limit)
        return [to_brief_track(it) for it in items if getattr(it, "name", None)]

    @sub.tool(tags={Tag.QUERY_METADATA})
    async def get_lyrics(track_uri: str) -> str | None:
        """Return lyrics for a track URI (best-effort).

        Different providers expose lyrics through different attributes; this
        tool surfaces the most common one (``metadata.lyrics``) and returns
        ``None`` if no lyrics are available.
        """
        item = await mass.music.get_item_by_uri(track_uri)
        metadata = getattr(item, "metadata", None)
        lyrics = getattr(metadata, "lyrics", None) if metadata else None
        return str(lyrics) if lyrics else None

    return sub
