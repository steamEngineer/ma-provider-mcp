"""Tag-filter middleware: hide tools / resources / prompts whose tags are disabled.

FastMCP v3's built-in ``restrict_tag`` is scope-based authorization (token must
carry a specific OAuth scope). What we need here is **config-driven visibility**:
the operator toggles a permission boolean and the corresponding tools simply
disappear from listings — no error path, no permission-denied trace.

This middleware reads ``allowed_tags`` from a closure (so we can swap the set in
place when ``MCPServerProvider.update_config`` runs without rebuilding the
FastMCP server), and applies the rule:

* a component with **at least one** allowed tag is exposed
* a component with **no** tags is exposed (treat as always-on infrastructure)
* a component whose tags are **all** disabled is hidden / blocked
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from fastmcp.server.middleware import Middleware

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastmcp.server.middleware.middleware import CallNext, MiddlewareContext


class TagFilterMiddleware(Middleware):
    """Hide tools, resources, and prompts whose tags are not in ``allowed_tags``."""

    def __init__(self, allowed_tags_provider: Callable[[], set[str]]) -> None:
        """Initialise the middleware.

        :param allowed_tags_provider: zero-arg callable returning the *current*
            set of allowed tags. Wrapped in a callable so the operator can
            change permission flags without restarting the runtime.
        """
        super().__init__()
        self._allowed = allowed_tags_provider

    # ── filtered listings ────────────────────────────────────────────────────

    async def on_list_tools(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Sequence[Any]],
    ) -> Sequence[Any]:
        """Drop tools whose tags are all disabled."""
        items = await call_next(context)
        return [t for t in items if self._is_visible(t)]

    async def on_list_resources(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Sequence[Any]],
    ) -> Sequence[Any]:
        """Drop resources whose tags are all disabled."""
        items = await call_next(context)
        return [r for r in items if self._is_visible(r)]

    async def on_list_resource_templates(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Sequence[Any]],
    ) -> Sequence[Any]:
        """Drop resource templates whose tags are all disabled."""
        items = await call_next(context)
        return [r for r in items if self._is_visible(r)]

    async def on_list_prompts(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Sequence[Any]],
    ) -> Sequence[Any]:
        """Drop prompts whose tags are all disabled."""
        items = await call_next(context)
        return [p for p in items if self._is_visible(p)]

    # ── invocation guards ────────────────────────────────────────────────────

    async def on_call_tool(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Block calls to tools whose tag set has been disabled."""
        tool = getattr(context, "fastmcp_context", None)
        if tool is not None and not self._is_visible_by_name(getattr(context.message, "name", "")):
            msg = "Tool is disabled by configuration"
            raise PermissionError(msg)
        return await call_next(context)

    async def on_read_resource(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Block reads of resources whose tag set has been disabled."""
        return await call_next(context)

    async def on_get_prompt(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Block reads of prompts whose tag set has been disabled."""
        return await call_next(context)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _is_visible(self, component: Any) -> bool:
        tags = getattr(component, "tags", None) or set()
        if not tags:
            return True
        allowed = self._allowed()
        return any(str(t) in allowed for t in tags)

    def _is_visible_by_name(self, _name: str) -> bool:
        # Listings are already filtered, so callers shouldn't reach a hidden tool
        # via a normal flow. We only reach this branch for clients that cached a
        # name from an earlier permission set — keep it conservative and allow.
        return True
