---
id: "0010"
title: "Library URI briefs and album/artist drill-down tools"
size: M
status: inprogress
priority: P1
effort_minutes: 20
feature_id:
---

## Problem Statement

MCP agents can search and list library items, but turning a Music Assistant URI
into structured data—or walking album→tracks / artist→albums—requires
re-scraping search results or guessing controller APIs. Wrong media types on a
URI silently return the wrong brief shape, and URI lookup errors are opaque.

## Solution Summary

Add read-only library tools that resolve a URI to the correct typed Brief,
plus drill-down tools for album track listings and artist discographies. Shared
URI resolution moves into the common helper layer with distinct ToolError
messages for not-found, malformed, and offline-provider cases.

## Acceptance Criteria

1. Five `library_get_*_by_uri` tools return typed Briefs and reject media-type
   mismatches with a recovery hint naming the correct tool.
2. `library_get_album_tracks` returns album + tracks sorted by disc/track
   number; unavailable tracks are omitted.
3. `library_get_artist_albums` returns artist + albums sorted by year (desc)
   then name; unavailable albums are omitted.
4. `TrackBrief` includes optional `disc_number` and `track_number` for
   drill-down ordering context.
5. Media and metadata tools reuse the shared resolver instead of duplicating
   lookup logic.

## Test Plan

- `tests/test_media_resolve.py` — resolver error classes, typed mismatch hints,
  and Brief conversion for each media type.
- `tests/test_library_album_tracks.py` — album/artist drill-down ordering and
  filtering of unavailable items.
- Manual: call `library_get_album_tracks` with a known album URI via MCP
  client and confirm track order matches the MA UI.

## Sequence Diagram

```mermaid
sequenceDiagram
    Agent->>LibraryTool: library_get_album_tracks(uri)
    LibraryTool->>MA: get_item_by_uri(uri)
    MA-->>LibraryTool: Album item
    LibraryTool->>MA: albums.tracks(id, provider)
    MA-->>LibraryTool: Track rows
    LibraryTool-->>Agent: AlbumTracksResult
```
