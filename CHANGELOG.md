# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-05-10

### Renamed
- Provider domain ``mcp_server`` → ``fastmcp_server``: the upstream
  sync target is now ``music_assistant/providers/fastmcp_server/``,
  disambiguating the plugin from the generic MCP-server term.

### Spec compliance (MCP 2025-06-18 / draft, RFC 8707, RFC 9728)
- ``Origin`` header validation in the ASGI bridge (Streamable HTTP
  MUST). Allowlist auto-derived from ``mass.webserver.{base_url,
  publish_ip}``; ``extra_allowed_origins`` config for reverse-proxy /
  HA ingress. IPv6 hosts re-bracketed correctly after URL parsing.
- RFC 9728 Protected Resource Metadata published at
  ``/.well-known/oauth-protected-resource[/<mount>]``;
  ``WWW-Authenticate: Bearer ... resource_metadata=…`` on 401.
  Live ``scopes_supported`` reflects permission hot-swaps.
- RFC 8707 audience binding via opt-in ``enforce_audience``
  (soft-mode default); ``AccessToken.resource`` populated.
- ``TagFilterMiddleware`` now blocks direct invocation of disabled
  tools / resources / prompts (closes the listing-only filter hole),
  raising the spec-correct error class per component kind.

### Tool UX
- ``ToolAnnotations`` (``title`` / ``readOnlyHint`` /
  ``destructiveHint`` / ``idempotentHint`` / ``openWorldHint``) on
  every tool — clients render labels and prompt before destructive
  ops.
- Per-tool execution timeouts (10s fast / 15s mutation / 30s query /
  60s bulk).
- ``ctx.info`` on search & recommendations; ``ctx.report_progress``
  on playlist bulk-add (per-item path for >10 tracks, with a
  partial-state warning on cancel/error).
- ``ctx.elicit(...)`` confirmation prompts on destructive ops
  (``clear_queue``, ``remove_tracks``, ``remove_from_favorites``,
  ``remove_from_library``); falls through gracefully when the client
  doesn't support elicitation.
- ``RecommendationFolderBrief`` dataclass for typed
  ``metadata.recommendations`` output.

### Bug fixes
- ``playlists.create_playlist``: kwarg ``provider_instance_or_domain``
  (was ``provider_instance_id_or_domain``).
- ``playlists.remove_playlist_tracks``: positions now passed as
  ``tuple[int, ...]`` (MA expects immutable).
- ``media.{add,remove}_from_{favorites,library}`` and ``mark_played``:
  resolve URI to a typed MediaItem first; MA expects
  ``(media_type, library_item_id)`` or a typed instance, not a raw
  URI.
- ``QueueBrief.item_count``: read from ``PlayerQueue.items`` (canonical
  total) instead of falling back to the truncated lookahead length.

### Tests
- 116 passing tests + e2e bridge loop (streaming, DELETE/GET, well-known).
- Consolidated ``FakeWebserver`` + ``build_aiohttp_app`` helpers in
  ``tests/conftest.py``; relative imports so the fixture resolves
  both locally and after sync into the fork's
  ``tests/providers/fastmcp_server/``.

### CI
- ``contents: read`` permission added to ``.github/workflows/test.yml``
  so reusable-test workflow can checkout the repo.
- Per-decorator ``# type: ignore[untyped-decorator]`` on every
  ``@sub.tool`` / ``@mcp.{prompt,resource}`` site for upstream
  ``music-assistant/server``'s strict mypy.
- ``# type: ignore[misc]`` on ``TagFilterMiddleware(Middleware)`` for
  ``disallow_subclassing_any``.
- Pre-existing TID252 (relative imports) / D401 / PLR0915 silenced
  with file-level pragmas.

### Notes
- ``enforce_audience`` ships in soft mode (default off). Switch to
  default-on once an upstream MA-core PR adds ``aud`` to issued JWTs.

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
