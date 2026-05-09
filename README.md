# ma-provider-mcp

**MCP Server** plugin provider for [Music Assistant](https://github.com/music-assistant/server).

Exposes MA's library, queue, playback, players, and metadata controllers as a
[Model Context Protocol](https://modelcontextprotocol.io/) server, accessible to
Claude Code, Codex, and any other MCP-aware LLM client.

## Highlights

- Built on **PrefectHQ FastMCP v3** — no homebrew SDK glue.
- **No core MA changes required.** Authentication delegates to
  `mass.webserver.auth.authenticate_with_token` (handles both JWT and legacy tokens).
- **16-permission tag-based access control** (query / control / edit / delete × 4 categories);
  defaults: reads on, all mutations off.
- **Mounted into MA's existing webserver** at `/mcp/v1` — reuses TLS, reverse proxy,
  and Home Assistant ingress out of the box. No second port, no extra firewall rule.
- 8 namespaced sub-servers, exposing tools as `library_search_tracks`,
  `queue_get_active_queue`, `playback_play_media`, etc.

## Usage

After enabling the plugin in MA settings:

```bash
TOKEN="<mint a token in MA Settings → Security → Tokens>"

# Probe streamable HTTP transport
curl -sS -H "Authorization: Bearer $TOKEN" \
     -H "Accept: text/event-stream" \
     http://localhost:8095/mcp/v1

# Connect Claude Code
claude mcp add ma --transport http \
  --url http://localhost:8095/mcp/v1 \
  --header "Authorization: Bearer $TOKEN"
```

## Permissions

The provider config exposes 16 permission booleans, grouped by category:

| Category   | Verbs                                                                |
|------------|----------------------------------------------------------------------|
| Query      | library, queue, players, metadata                                    |
| Control    | playback, volume, players, media (announcements)                     |
| Edit       | library (add), queue (move/save), playlists (create/add/reorder), favorites (add) |
| Delete     | library (remove), queue (clear), playlists (delete), favorites (remove) |

Each maps to a tag (`query:library`, `control:playback`, …). FastMCP's
`restrict_tag` middleware filters `tools/list`, `resources/list`, and
`prompts/list` so disabled tools are **invisible** to clients (no permission-denied
trace leaks).

## Development

```bash
uv sync --all-extras
uv run pytest
uv run ruff check provider tests
uv run mypy provider
```

## License

[Apache-2.0](LICENSE)
