"""Shared pytest fixtures for ma-provider-mcp tests.

Most tests run without a real Music Assistant install — they exercise pure
logic (URI parsing, tag mapping, config entries shape) or use ``MagicMock``
for ``mass``. Integration-level tests that need a real MA stack are marked
with ``@pytest.mark.integration`` and skipped by default.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

# Make the provider/ package importable as a top-level "provider" module without
# requiring a full ``pip install -e .`` step in ad-hoc test runs.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture
def mock_user() -> MagicMock:
    """A minimal stand-in for an MA ``User`` object."""
    user = MagicMock()
    user.user_id = "u1"
    user.username = "tester"
    user.role = MagicMock(value="admin")
    user.enabled = True
    return user


@pytest.fixture
def mock_mass(mock_user: MagicMock) -> MagicMock:
    """A MusicAssistant stub with the surface area we touch."""
    mass = MagicMock()
    mass.webserver = MagicMock()
    mass.webserver.base_url = "http://localhost:8095"
    mass.webserver.publish_ip = "127.0.0.1"
    mass.webserver.auth = MagicMock()
    mass.webserver.auth.authenticate_with_token = AsyncMock(return_value=mock_user)
    mass.webserver.register_dynamic_route = MagicMock(return_value=lambda: None)

    mass.music = MagicMock()
    mass.music.search = AsyncMock()
    mass.music.recently_added_tracks = AsyncMock(return_value=[])
    mass.music.recently_played = AsyncMock(return_value=[])
    mass.music.recommendations = AsyncMock(return_value=[])
    mass.music.get_item_by_uri = AsyncMock()

    mass.music.tracks.library_items = AsyncMock(return_value=[])
    mass.music.tracks.get_library_item = AsyncMock()
    mass.music.albums.library_items = AsyncMock(return_value=[])
    mass.music.albums.get_library_item = AsyncMock()
    mass.music.artists.library_items = AsyncMock(return_value=[])
    mass.music.artists.get_library_item = AsyncMock()
    mass.music.playlists.library_items = AsyncMock(return_value=[])
    mass.music.playlists.get_library_item = AsyncMock()
    mass.music.playlists.create_playlist = AsyncMock()
    mass.music.playlists.add_playlist_track = AsyncMock()
    mass.music.playlists.add_playlist_tracks = AsyncMock()
    mass.music.playlists.remove_playlist_tracks = AsyncMock()
    mass.music.radio.library_items = AsyncMock(return_value=[])
    mass.music.radio.get_library_item = AsyncMock()
    mass.music.add_item_to_favorites = AsyncMock()
    mass.music.remove_item_from_favorites = AsyncMock()
    mass.music.add_item_to_library = AsyncMock()
    mass.music.remove_item_from_library = AsyncMock()
    mass.music.mark_item_played = AsyncMock()

    mass.player_queues = MagicMock()
    mass.player_queues.get_active_queue = MagicMock(return_value=None)
    mass.player_queues.get = MagicMock(return_value=None)
    mass.player_queues.items = MagicMock(return_value=[])
    mass.player_queues.play_media = AsyncMock()
    mass.player_queues.play_pause = AsyncMock()
    mass.player_queues.stop = AsyncMock()
    mass.player_queues.next = AsyncMock()
    mass.player_queues.previous = AsyncMock()
    mass.player_queues.skip = AsyncMock()
    mass.player_queues.seek = AsyncMock()
    mass.player_queues.play_index = AsyncMock()
    mass.player_queues.set_shuffle = AsyncMock()
    mass.player_queues.transfer_queue = AsyncMock()
    mass.player_queues.clear = AsyncMock()

    mass.players = MagicMock()
    mass.players.all_players = MagicMock(return_value=[])
    mass.players.get = MagicMock(return_value=None)
    mass.players.cmd_power = AsyncMock()
    mass.players.cmd_group = AsyncMock()
    mass.players.cmd_volume_set = AsyncMock()
    mass.players.cmd_volume_up = AsyncMock()
    mass.players.cmd_volume_down = AsyncMock()
    mass.players.cmd_volume_mute = AsyncMock()
    mass.players.cmd_group_volume = AsyncMock()
    mass.players.play_announcement = AsyncMock()

    return mass


@pytest.fixture
def mock_config() -> MagicMock:
    """A ProviderConfig stub. ``get_value`` returns whatever is set in ``_values``."""
    config = MagicMock()
    config._values = {
        # Defaults match build_config_entries
        "require_auth": True,
        "mount_path": "/mcp/v1",
        "extra_allowed_origins": "",
        "enforce_audience": False,
        "query_library": True,
        "query_queue": True,
        "query_players": True,
        "query_metadata": True,
        "control_playback": False,
        "control_volume": False,
        "control_players": False,
        "control_media": False,
        "edit_library": False,
        "edit_queue": False,
        "edit_playlists": False,
        "edit_favorites": False,
        "delete_library": False,
        "delete_queue": False,
        "delete_playlists": False,
        "delete_favorites": False,
        "res_library": True,
        "res_player": True,
        "res_prompts": True,
    }

    def _get(key: str, default: Any = None) -> Any:
        return config._values.get(key, default)

    config.get_value = MagicMock(side_effect=_get)
    return config


@pytest.fixture
def have_fastmcp() -> bool:
    """True if ``fastmcp`` is importable in the current environment."""
    return importlib.util.find_spec("fastmcp") is not None


def pytest_collection_modifyitems(config: Any, items: Iterator[Any]) -> None:
    """Skip integration tests by default unless ``--run-integration`` is passed."""
    if config.getoption("--run-integration", default=False):
        return
    skip_integration = pytest.mark.skip(reason="integration tests require --run-integration")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


def pytest_addoption(parser: Any) -> None:
    """Add the ``--run-integration`` CLI flag."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run tests marked @pytest.mark.integration",
    )
