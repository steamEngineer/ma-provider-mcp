"""Queue: read state and edit / delete queue items."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..models import QueueBrief
from ..tags import Tag
from ._common import to_brief_queue

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant


def build_queue_server(mass: MusicAssistant) -> FastMCP:
    """Construct the ``queue/*`` sub-server."""
    sub: FastMCP = FastMCP(name="queue")

    @sub.tool(
        tags={Tag.QUERY_QUEUE},
        annotations=ToolAnnotations(
            title="Get active queue",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def get_active_queue(player_id: str, include_items: int = 25) -> QueueBrief:
        """Return the active queue for a player, including up to ``include_items`` lookahead."""
        queue = mass.player_queues.get_active_queue(player_id)
        if queue is None:
            return QueueBrief(
                queue_id="", current_index=None, item_count=0, shuffle=False, repeat="off"
            )
        raw = mass.player_queues.items(queue.queue_id)
        items = list(raw)[: max(0, include_items)] if include_items > 0 else []
        return to_brief_queue(queue, items=items)

    @sub.tool(
        tags={Tag.EDIT_QUEUE},
        annotations=ToolAnnotations(
            title="Toggle queue shuffle",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def set_shuffle(queue_id: str, enabled: bool) -> None:
        """Enable or disable shuffle on the given queue."""
        await mass.player_queues.set_shuffle(queue_id, enabled)

    @sub.tool(
        tags={Tag.DELETE_QUEUE},
        annotations=ToolAnnotations(
            title="Clear queue",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def clear_queue(queue_id: str) -> None:
        """Clear all items from the given queue.

        Implementation note: MA's ``player_queues`` exposes a ``clear`` method;
        if the API name diverges, this is the single integration point to fix.
        """
        clear = getattr(mass.player_queues, "clear", None)
        if clear is None:
            msg = "mass.player_queues.clear is not available on this MA build"
            raise RuntimeError(msg)
        await clear(queue_id)

    @sub.tool(
        tags={Tag.CONTROL_PLAYBACK},
        annotations=ToolAnnotations(
            title="Transfer queue between players",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def transfer_queue(source_queue_id: str, target_queue_id: str) -> None:
        """Move a queue from one player to another."""
        await mass.player_queues.transfer_queue(source_queue_id, target_queue_id)

    return sub
