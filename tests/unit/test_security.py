import pytest
from unittest.mock import AsyncMock, patch

from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_magic_link_token,
    create_refresh_token,
    decode_token,
    get_user_id_from_refresh_token,
    hash_password,
    revoke_refresh_token,
    verify_magic_link_token,
    verify_password,
)


def test_hash_password_and_verify():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_hash_password_bcrypt_prefix():
    hashed = hash_password("test")
    assert hashed.startswith("$2b$")


def test_access_token_create_and_decode():
    token = create_access_token("user-1", "tenant-1", "student", company_id="company-1")
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == "tenant-1"
    assert payload["role"] == "student"
    assert payload["company_id"] == "company-1"


def test_access_token_without_company_id():
    token = create_access_token("user-2", "tenant-2", "admin")
    payload = decode_token(token)
    assert payload["company_id"] is None


def test_access_token_decode_invalid():
    with pytest.raises(AppError) as exc_info:
        decode_token("invalid.token.here")
    assert exc_info.value.error_def.http_status == 401


def test_access_token_decode_tampered():
    token = create_access_token("user-1", "tenant-1", "admin")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(AppError) as exc_info:
        decode_token(tampered)
    assert exc_info.value.error_def.http_status == 401


@pytest.mark.asyncio
async def test_refresh_token_create_stores_in_redis():
    mock_redis = AsyncMock()
    with patch("app.core.security.get_redis", return_value=mock_redis):
        token = await create_refresh_token("user-1")
        assert len(token) == 36  # UUID format
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == f"refresh:{token}"
        assert call_args[0][2] == "user-1"


@pytest.mark.asyncio
async def test_refresh_token_get_user_id():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "user-1"
    with patch("app.core.security.get_redis", return_value=mock_redis):
        user_id = await get_user_id_from_refresh_token("some-token")
        assert user_id == "user-1"
        mock_redis.get.assert_called_once_with("refresh:some-token")


@pytest.mark.asyncio
async def test_refresh_token_revoke():
    mock_redis = AsyncMock()
    with patch("app.core.security.get_redis", return_value=mock_redis):
        await revoke_refresh_token("some-token")
        mock_redis.delete.assert_called_once_with("refresh:some-token")


@pytest.mark.asyncio
async def test_magic_link_create_stores_in_redis():
    mock_redis = AsyncMock()
    with patch("app.core.security.get_redis", return_value=mock_redis):
        token = await create_magic_link_token("user@example.com")
        assert len(token) == 36
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == f"magic_link:{token}"
        assert call_args[0][2] == "user@example.com"


@pytest.mark.asyncio
async def test_magic_link_verify_returns_email():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "user@example.com"
    with patch("app.core.security.get_redis", return_value=mock_redis):
        email = await verify_magic_link_token("some-token")
        assert email == "user@example.com"


@pytest.mark.asyncio
async def test_magic_link_verify_deletes_key():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "user@example.com"
    with patch("app.core.security.get_redis", return_value=mock_redis):
        await verify_magic_link_token("some-token")
        mock_redis.delete.assert_called_once_with("magic_link:some-token")


@pytest.mark.asyncio
async def test_magic_link_verify_invalid():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    with patch("app.core.security.get_redis", return_value=mock_redis):
        with pytest.raises(AppError) as exc_info:
            await verify_magic_link_token("nonexistent-token")
        assert exc_info.value.error_def.http_status == 401
