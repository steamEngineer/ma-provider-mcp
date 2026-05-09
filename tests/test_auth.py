"""Tests for ``provider.auth.MASTokenVerifier``."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from provider.auth import MASTokenVerifier


@pytest.mark.asyncio
async def test_valid_token_returns_access_token(mock_mass: MagicMock, mock_user: MagicMock) -> None:
    """A valid token yields an AccessToken with the user's role mapped to scopes."""
    mock_mass.webserver.auth.authenticate_with_token = AsyncMock(return_value=mock_user)
    verifier = MASTokenVerifier(mock_mass)

    token = await verifier.verify_token("valid-token")

    assert token is not None
    assert token.client_id == "u1"
    assert token.scopes == ["admin"]
    assert token.token == "valid-token"


@pytest.mark.asyncio
async def test_invalid_token_returns_none(mock_mass: MagicMock) -> None:
    """An invalid (rejected) token returns None."""
    mock_mass.webserver.auth.authenticate_with_token = AsyncMock(return_value=None)
    verifier = MASTokenVerifier(mock_mass)
    assert await verifier.verify_token("nope") is None


@pytest.mark.asyncio
async def test_disabled_user_returns_none(mock_mass: MagicMock, mock_user: MagicMock) -> None:
    """A user marked disabled is rejected even if the token is valid."""
    mock_user.enabled = False
    mock_mass.webserver.auth.authenticate_with_token = AsyncMock(return_value=mock_user)
    verifier = MASTokenVerifier(mock_mass)
    assert await verifier.verify_token("valid-but-disabled") is None


@pytest.mark.asyncio
async def test_authenticate_called_once(mock_mass: MagicMock, mock_user: MagicMock) -> None:
    """We delegate exactly once per verify_token call (no retry storm)."""
    mock_mass.webserver.auth.authenticate_with_token = AsyncMock(return_value=mock_user)
    verifier = MASTokenVerifier(mock_mass)
    await verifier.verify_token("t")
    mock_mass.webserver.auth.authenticate_with_token.assert_awaited_once_with("t")


@pytest.mark.asyncio
async def test_underlying_exception_swallowed(mock_mass: MagicMock) -> None:
    """If MA's auth raises, we log and return None — never propagate."""
    mock_mass.webserver.auth.authenticate_with_token = AsyncMock(
        side_effect=RuntimeError("db down")
    )
    verifier = MASTokenVerifier(mock_mass)
    assert await verifier.verify_token("any") is None
