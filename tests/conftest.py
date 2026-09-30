"""Shared fixtures for the Rustatio integration tests."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rustatio.const import CONF_BASE_URL, CONF_TOKEN, DOMAIN

BASE_URL = "http://rustatio.test:8080"
TOKEN = "test-token"

INSTANCE_SUMMARIES = [
    {
        "id": "torrent-a",
        "name": "Torrent A",
        "infoHash": "a" * 40,
        "state": "running",
        "isTrackerInvalid": False,
        "trackerError": None,
        "totalSize": 500_000_000_000,
        "uploaded": 1_000_000_000,
        "downloaded": 500_000_000,
        "currentUploadRate": 10.0,
        "currentDownloadRate": 1.0,
        "source": "watch_folder",
    },
    {
        "id": "torrent-b",
        "name": "Torrent B",
        "infoHash": "b" * 40,
        "state": "stopped",
        "isTrackerInvalid": True,
        "trackerError": "Tracker returned HTTP 503",
        "totalSize": 700_000_000_000,
        "uploaded": 500_000_000,
        "downloaded": 500_000_000,
        "currentUploadRate": 0.0,
        "currentDownloadRate": 0.0,
        "source": "watch_folder",
    },
    {
        "id": "torrent-c",
        "name": "Torrent C",
        "infoHash": "c" * 40,
        "state": "idle",
        "isTrackerInvalid": False,
        "trackerError": None,
        "totalSize": 300_000_000_000,
        "uploaded": 500_000_000,
        "downloaded": 0,
        "currentUploadRate": 2.5,
        "currentDownloadRate": 0.0,
        "source": "manual",
    },
]

WATCH_STATUS = {
    "enabled": True,
    "watch_dir": "/torrents",
    "auto_start": False,
    "file_count": 4,
    "loaded_count": 3,
}


@dataclass
class MockRustatioApi:
    """References to the mocked Rustatio API methods."""

    summaries: AsyncMock
    watch_status: AsyncMock


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable loading integrations from custom_components."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a configured Rustatio entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Rustatio",
        data={
            CONF_BASE_URL: BASE_URL,
            CONF_TOKEN: TOKEN,
        },
    )


@pytest.fixture
def mock_rustatio_api() -> Generator[MockRustatioApi]:
    """Mock the two Rustatio endpoints used by the integration."""
    with (
        patch(
            "custom_components.rustatio.api.RustatioApi.async_get_instance_summaries",
            new_callable=AsyncMock,
            return_value=INSTANCE_SUMMARIES,
        ) as summaries,
        patch(
            "custom_components.rustatio.api.RustatioApi.async_get_watch_status",
            new_callable=AsyncMock,
            return_value=WATCH_STATUS,
        ) as watch_status,
    ):
        yield MockRustatioApi(
            summaries=summaries,
            watch_status=watch_status,
        )


@pytest.fixture
async def setup_rustatio(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_rustatio_api: MockRustatioApi,
) -> MockConfigEntry:
    """Set up the Rustatio integration and return its config entry."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
