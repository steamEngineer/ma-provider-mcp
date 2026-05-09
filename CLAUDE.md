# CLAUDE.md — ma-provider-mcp

## Repo purpose

Provider repo for the Music Assistant `mcp_server` plugin. Synced into the
`trudenboy/ma-server` fork via `ma-provider-tools` automation
(`reusable-sync-to-fork.yml`).

## Architecture

- `provider/` — runtime code; `manifest.json` declares `type=plugin`, `domain=mcp_server`.
- `provider/server.py::MCPServerRuntime` builds a root `FastMCP`, mounts 8 sub-servers
  by namespace, registers resources/prompts, applies `restrict_tag` middleware, and
  mounts the streamable-HTTP ASGI app under MA's webserver via `http_bridge.py`.
- `provider/auth.py::MASTokenVerifier` is the only auth code — delegates to
  `mass.webserver.auth.authenticate_with_token`.
- `provider/tags.py` maps the 16 permission `ConfigEntry` booleans to FastMCP tags.

## Conventions

- Sphinx-style docstrings with `:param:` syntax (matches MA core).
- No comments explaining obvious code; only WHY-comments for non-obvious decisions.
- Stdlib `dataclass` for response shapes (FastMCP auto-generates JSON schema).
- Reuse `music_assistant_models` types in resource responses; use `*Brief` dataclasses
  in tool responses to keep payloads small for LLM context.
- Tool decorators always include `tags={Tag.…}` — never untagged.

## Key external APIs

- `mass.webserver.register_dynamic_route(path, handler, method="*") -> Callable[[], None]`
- `mass.webserver.auth.authenticate_with_token(token) -> User | None`
- `mass.webserver.base_url`, `mass.webserver.publish_ip`
- `mass.music.{search,artists,albums,tracks,playlists,radio,podcasts,audiobooks}`
- `mass.players`, `mass.player_queues`

## Testing

In-memory FastMCP `Client` transport (no HTTP). Reuse the canonical `mass` fixture
from MA's `tests/conftest.py` rather than mocking `mass.music`.

## Auto-generated files

`pyproject.toml`, `ruff.toml`, `.pre-commit-config.yaml`, and `.github/workflows/*.yml`
are templated by `ma-provider-tools` and will be regenerated on registry update —
do not hand-edit.
