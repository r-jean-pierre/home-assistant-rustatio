"""Tests for the Rustatio HTTP client."""

from __future__ import annotations

from aiohttp import ClientConnectionError
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.rustatio.api import (
    RustatioApi,
    RustatioApiError,
    RustatioAuthError,
    RustatioConnectionError,
)

from .conftest import BASE_URL, INSTANCE_SUMMARIES, WATCH_STATUS


async def test_api_success_and_bearer_token(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test successful API responses and optional bearer authentication."""
    aioclient_mock.get(
        f"{BASE_URL}/api/instances/summary",
        json={"success": True, "data": INSTANCE_SUMMARIES},
    )
    aioclient_mock.get(
        f"{BASE_URL}/api/watch/status",
        json={"success": True, "data": WATCH_STATUS},
    )

    api = RustatioApi(
        async_get_clientsession(hass),
        BASE_URL + "/",
        "secret-token",
    )

    assert await api.async_get_instance_summaries() == INSTANCE_SUMMARIES
    assert await api.async_get_watch_status() == WATCH_STATUS

    assert aioclient_mock.call_count == 2
    for _method, _url, _data, headers in aioclient_mock.mock_calls:
        assert headers["Authorization"] == "Bearer secret-token"


async def test_api_without_token(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test that no Authorization header is sent when no token is configured."""
    aioclient_mock.get(
        f"{BASE_URL}/api/watch/status",
        json={"success": True, "data": WATCH_STATUS},
    )

    api = RustatioApi(async_get_clientsession(hass), BASE_URL, None)
    assert await api.async_get_watch_status() == WATCH_STATUS

    assert aioclient_mock.mock_calls[0][3] == {}


@pytest.mark.parametrize("status", [401, 403])
async def test_api_auth_errors(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    status: int,
) -> None:
    """Test authentication failures."""
    aioclient_mock.get(
        f"{BASE_URL}/api/instances/summary",
        status=status,
        json={"success": False, "error": "Authentication failed"},
    )

    api = RustatioApi(async_get_clientsession(hass), BASE_URL, "bad-token")

    with pytest.raises(RustatioAuthError):
        await api.async_get_instance_summaries()


async def test_api_http_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test a non-auth HTTP error."""
    aioclient_mock.get(
        f"{BASE_URL}/api/instances/summary",
        status=500,
        json={"success": False, "error": "Internal error"},
    )

    api = RustatioApi(async_get_clientsession(hass), BASE_URL)

    with pytest.raises(RustatioApiError, match="HTTP 500"):
        await api.async_get_instance_summaries()


async def test_api_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test a network-level connection failure."""
    aioclient_mock.get(
        f"{BASE_URL}/api/instances/summary",
        exc=ClientConnectionError("offline"),
    )

    api = RustatioApi(async_get_clientsession(hass), BASE_URL)

    with pytest.raises(RustatioConnectionError):
        await api.async_get_instance_summaries()


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        ({"success": False, "data": []}, "Unexpected Rustatio API response"),
        (["not", "an", "object"], "invalid JSON"),
    ],
)
async def test_api_invalid_envelope(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    payload: object,
    expected_message: str,
) -> None:
    """Test malformed API envelopes."""
    aioclient_mock.get(
        f"{BASE_URL}/api/instances/summary",
        json=payload,
    )

    api = RustatioApi(async_get_clientsession(hass), BASE_URL)

    with pytest.raises(RustatioApiError, match=expected_message):
        await api.async_get_instance_summaries()


async def test_api_invalid_json(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test a response body that is not valid JSON."""
    aioclient_mock.get(
        f"{BASE_URL}/api/instances/summary",
        text="not-json",
    )

    api = RustatioApi(async_get_clientsession(hass), BASE_URL)

    with pytest.raises(RustatioApiError, match="invalid JSON"):
        await api.async_get_instance_summaries()


@pytest.mark.parametrize(
    ("path", "payload", "method_name", "expected_message"),
    [
        (
            "/api/instances/summary",
            {"success": True, "data": {"unexpected": "object"}},
            "async_get_instance_summaries",
            "unexpected format",
        ),
        (
            "/api/instances/summary",
            {"success": True, "data": ["not-an-object"]},
            "async_get_instance_summaries",
            "unexpected format",
        ),
        (
            "/api/watch/status",
            {"success": True, "data": []},
            "async_get_watch_status",
            "not an object",
        ),
    ],
)
async def test_api_invalid_data_shape(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    path: str,
    payload: object,
    method_name: str,
    expected_message: str,
) -> None:
    """Test endpoint-specific data validation."""
    aioclient_mock.get(f"{BASE_URL}{path}", json=payload)

    api = RustatioApi(async_get_clientsession(hass), BASE_URL)

    with pytest.raises(RustatioApiError, match=expected_message):
        await getattr(api, method_name)()
