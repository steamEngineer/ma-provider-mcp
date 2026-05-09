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
