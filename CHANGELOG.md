# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] — 2026-05-10

### Fixed
- **Streamable-HTTP endpoint returned 404** for every request. The
  bridge stripped ``mount_path`` (``/mcp/v1``) before handing the
  request to FastMCP's ASGI app, but FastMCP's internal Starlette
  router lives at its default ``streamable_http_path`` (``/mcp``) — so
  after the strip the path no longer matched any FastMCP route. Fix:
  pass our ``mount_path`` to ``mcp.http_app(path=…)`` and stop
  stripping in the bridge so the URL FastMCP receives is the URL it
  routes on. Caught manually by ``claude mcp add`` reporting "Failed
  to connect"; e2e tests didn't catch it because the in-test ``_Mcp``
  fake exposed an ASGI app that ignored path-routing entirely.

## [0.2.1] — 2026-05-10

### Added
- ``provider/icon.svg`` and ``provider/icon_monochrome.svg`` — the canonical
  Model Context Protocol logo (973-byte SVG from Wikimedia Commons),
  picked up by Music Assistant via the standard ``icon.svg`` /
  ``icon_monochrome.svg`` convention next to ``manifest.json``.

### CI
- Drop ``pytest.importorskip("fastmcp")`` from test files so ruff's isort
  hook keeps a single contiguous third-party group after sync into
  ``music_assistant/providers/fastmcp_server/``.
- File-level ``# mypy: disable-error-code="..."`` in test files (quoted
  CSV — unquoted form trips mypy's option parser).
- ``# type: ignore[..., unused-ignore]`` on every suppression so both
  the relaxed ``ma-provider-tools/reusable-test`` mypy and upstream
  ``music-assistant/server`` strict mypy pass without complaining
  about each other's unused suppressions.

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

## [0.1.0] — initial scaffold

### Added
- Initial scaffold of the MCP Server plugin provider for Music Assistant.
- PrefectHQ FastMCP v3 integration (no manual SDK glue).
- 16-permission tag-based access control (query / control / edit / delete × 4 categories).
- ASGI bridge mounting FastMCP into MA's main aiohttp webserver under `/mcp/v1`.
- 8 sub-servers (`library`, `queue`, `playback`, `players`, `playlists`,
  `volume`, `media`, `metadata`); `library://`, `player://`, `queue://`
  resources; canned prompts.
