"""Tests for the Rustatio config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rustatio.api import (
    RustatioApiError,
    RustatioAuthError,
    RustatioConnectionError,
)
from custom_components.rustatio.const import CONF_BASE_URL, CONF_TOKEN, DOMAIN

from .conftest import BASE_URL, TOKEN, MockRustatioApi


async def test_user_flow_success(
    hass: HomeAssistant,
    mock_rustatio_api: MockRustatioApi,
) -> None:
    """Test successful initial configuration and input normalization."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BASE_URL: "  http://rustatio.test:8080/  ",
            CONF_TOKEN: "  test-token  ",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Rustatio"
    assert result["data"] == {
        CONF_BASE_URL: BASE_URL,
        CONF_TOKEN: TOKEN,
    }


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (RustatioConnectionError("offline"), "cannot_connect"),
        (RustatioAuthError("denied"), "invalid_auth"),
        (RustatioApiError("bad response"), "invalid_response"),
        (RuntimeError("unexpected"), "unknown"),
    ],
)
async def test_user_flow_recovers_from_validation_errors(
    hass: HomeAssistant,
    mock_rustatio_api: MockRustatioApi,
    error: Exception,
    expected: str,
) -> None:
    """Test validation errors and recovery in the same config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    mock_rustatio_api.summaries.side_effect = error

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BASE_URL: BASE_URL,
            CONF_TOKEN: TOKEN,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}

    mock_rustatio_api.summaries.side_effect = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BASE_URL: BASE_URL,
            CONF_TOKEN: TOKEN,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_validates_watch_status(
    hass: HomeAssistant,
    mock_rustatio_api: MockRustatioApi,
) -> None:
    """Test that both Rustatio endpoints are validated during setup."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    mock_rustatio_api.watch_status.side_effect = RustatioApiError("bad watch data")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BASE_URL: BASE_URL,
            CONF_TOKEN: "",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_response"}


async def test_duplicate_server_is_rejected(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_rustatio_api: MockRustatioApi,
) -> None:
    """Test duplicate base URLs are not allowed."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BASE_URL: BASE_URL,
            CONF_TOKEN: "",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_rustatio_api: MockRustatioApi,
) -> None:
    """Test changing the Rustatio URL and token."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BASE_URL: "http://new-rustatio.test:8080/",
            CONF_TOKEN: "new-token",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data == {
        CONF_BASE_URL: "http://new-rustatio.test:8080",
        CONF_TOKEN: "new-token",
    }

    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_reconfigure_rejects_duplicate_server(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_rustatio_api: MockRustatioApi,
) -> None:
    """Test reconfigure cannot collide with another Rustatio entry."""
    mock_config_entry.add_to_hass(hass)
    second_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Other Rustatio",
        data={
            CONF_BASE_URL: "http://other-rustatio.test:8080",
            CONF_TOKEN: "",
        },
    )
    second_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BASE_URL: "http://other-rustatio.test:8080",
            CONF_TOKEN: "",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_rustatio_api: MockRustatioApi,
) -> None:
    """Test replacing a rejected Rustatio token."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: "replacement-token"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_TOKEN] == "replacement-token"

    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_reauth_recovers_from_invalid_token(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_rustatio_api: MockRustatioApi,
) -> None:
    """Test a reauthentication flow can recover from another bad token."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )

    mock_rustatio_api.summaries.side_effect = RustatioAuthError("denied")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: "still-wrong"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    mock_rustatio_api.summaries.side_effect = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: ""},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_TOKEN] == ""

    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
