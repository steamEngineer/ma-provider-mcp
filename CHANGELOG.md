# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial scaffold of the MCP Server plugin provider for Music Assistant.
- PrefectHQ FastMCP v3 integration (no manual SDK glue).
- 16-permission tag-based access control (query / control / edit / delete × 4 categories).
- ASGI bridge mounting FastMCP into MA's main aiohttp webserver under `/mcp/v1`.
- `MASTokenVerifier` delegating to `mass.webserver.auth.authenticate_with_token`
  (supports JWT and legacy hash tokens — no core MA changes required).
- 8 sub-servers: `library`, `queue`, `playback`, `players`, `playlists`, `volume`,
  `media`, `metadata`.
- `library://`, `player://`, `queue://` MCP resources.
- Canned prompts: `find_and_play`, `curate_party_playlist`, `now_playing_summary`.

### Spec compliance (MCP 2025-06-18 / draft, RFC 8707, RFC 9728)
- **Origin validation** (Streamable HTTP MUST): the bridge rejects requests
  from non-allow-listed `Origin` headers with HTTP 403, mitigating DNS
  rebinding. Allowlist auto-derived from `mass.webserver.{base_url, publish_ip}`
  + loopback; advanced config `extra_allowed_origins` (CSV) for reverse-proxy.
- **Protected Resource Metadata** (RFC 9728): server publishes the metadata
  document at `/.well-known/oauth-protected-resource[/<mount>]` and FastMCP
  appends `resource_metadata="…"` to `WWW-Authenticate` on 401.
- **Audience binding** (RFC 8707): opt-in `enforce_audience` rejects tokens
  whose `aud` claim doesn't match the canonical resource URI. Ships in soft
  mode by default — logs a warning so existing tokens keep working until MA
  upstream issues audience-bound JWTs.
- **TagFilterMiddleware enforcement on direct invocation**: a client cannot
  bypass the listing filter by calling a disabled tool / reading a disabled
  resource / requesting a disabled prompt by name. Lookup now goes through
  the public `mcp.get_*` API.

### Tool UX
- `ToolAnnotations` (`title`, `readOnlyHint`, `destructiveHint`,
  `idempotentHint`, `openWorldHint`) on every tool — clients can render
  human-readable labels and prompt before destructive operations.
- Per-tool execution timeouts (10s fast / 15s mutation / 30s query / 60s bulk).
- `ctx.info` / `ctx.report_progress` injection in long-running tools
  (search, recommendations, playlist bulk-add).
- **Elicitation** prompts on destructive operations (`clear_queue`,
  `remove_tracks`, `remove_from_favorites`, `remove_from_library`).
  Falls through gracefully when client doesn't support elicitation.
- `RecommendationFolderBrief` dataclass for `metadata.recommendations`
  (typed `outputSchema` instead of `Any`).

### Notes
- Audience binding is currently soft-mode-only because MA core tokens don't
  yet carry `aud`. Upstream PR planned: emit `aud` per token in MA's JWT
  issuer.
