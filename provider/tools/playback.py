"""Playback: play, pause, seek, skip, play media."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import FastMCP

from ..tags import Tag

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant


def build_playback_server(mass: MusicAssistant) -> FastMCP:
    """Construct the ``playback/*`` sub-server."""
    sub: FastMCP = FastMCP(name="playback")

    @sub.tool(tags={Tag.CONTROL_PLAYBACK})
    async def play_pause(queue_id: str) -> None:
        """Toggle play/pause on the given queue."""
        await mass.player_queues.play_pause(queue_id)

    @sub.tool(tags={Tag.CONTROL_PLAYBACK})
    async def stop(queue_id: str) -> None:
        """Stop playback on the given queue."""
        await mass.player_queues.stop(queue_id)

    @sub.tool(tags={Tag.CONTROL_PLAYBACK})
    async def next_track(queue_id: str) -> None:
        """Advance to the next track."""
        await mass.player_queues.next(queue_id)

    @sub.tool(tags={Tag.CONTROL_PLAYBACK})
    async def previous_track(queue_id: str) -> None:
        """Return to the previous track."""
        await mass.player_queues.previous(queue_id)

    @sub.tool(tags={Tag.CONTROL_PLAYBACK})
    async def skip(queue_id: str, seconds: int = 10) -> None:
        """Skip forward by ``seconds`` (or backward when negative)."""
        await mass.player_queues.skip(queue_id, seconds)

    @sub.tool(tags={Tag.CONTROL_PLAYBACK})
    async def seek(queue_id: str, position: int) -> None:
        """Seek to absolute position (seconds) in the current track."""
        await mass.player_queues.seek(queue_id, position)

    @sub.tool(tags={Tag.CONTROL_PLAYBACK})
    async def play_media(
        queue_id: str,
        uri: str,
        radio_mode: bool = False,
    ) -> None:
        """Play media on the given queue by MA URI.

        :param queue_id: queue to play on (typically the player_id).
        :param uri: MA URI of the media to play (artist, album, track, playlist, radio).
        :param radio_mode: when ``True``, MA fills the queue with similar items.
        """
        await mass.player_queues.play_media(queue_id, uri, radio_mode=radio_mode)

    @sub.tool(tags={Tag.CONTROL_PLAYBACK})
    async def play_index(queue_id: str, index: int) -> None:
        """Play the queue item at the given zero-based index."""
        await mass.player_queues.play_index(queue_id, index)

    return sub
