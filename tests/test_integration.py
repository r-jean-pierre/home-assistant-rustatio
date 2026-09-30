"""Integration-level tests for Rustatio entities."""

from __future__ import annotations

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rustatio.api import RustatioConnectionError

from .conftest import INSTANCE_SUMMARIES, MockRustatioApi


def _state(hass: HomeAssistant, entity_id: str) -> State:
    """Return an entity state and fail clearly if the entity is missing."""
    state = hass.states.get(entity_id)
    assert state is not None
    return state


async def test_entities_expose_expected_aggregates(
    hass: HomeAssistant,
    setup_rustatio: MockConfigEntry,
) -> None:
    """Test the public Home Assistant entity states."""
    managed = _state(hass, "sensor.rustatio_managed_torrents")
    assert managed.state == "3"
    assert managed.attributes["torrent_states"] == {
        "running": 1,
        "stopped": 1,
        "idle": 1,
    }
    assert managed.attributes["torrent_sources"] == {
        "watch_folder": 2,
        "manual": 1,
    }

    assert _state(hass, "sensor.rustatio_running_torrents").state == "1"
    assert (
        _state(hass, "sensor.rustatio_torrents_with_tracker_errors").state
        == "1"
    )

    watch = _state(hass, "sensor.rustatio_torrent_files_in_watch_folder")
    assert watch.state == "4"
    assert watch.attributes["loaded_torrent_files"] == 3
    assert watch.attributes["watch_enabled"] is True
    assert watch.attributes["watch_folder"] == "/torrents"
    assert watch.attributes["auto_start"] is False

    upload_rate = _state(hass, "sensor.rustatio_simulated_upload_rate")
    assert float(upload_rate.state) == pytest.approx(12.5)
    assert upload_rate.attributes[ATTR_UNIT_OF_MEASUREMENT] == "kB/s"

    download_rate = _state(hass, "sensor.rustatio_simulated_download_rate")
    assert float(download_rate.state) == pytest.approx(1.0)
    assert download_rate.attributes[ATTR_UNIT_OF_MEASUREMENT] == "kB/s"

    total_size = _state(hass, "sensor.rustatio_total_torrent_size")
    assert float(total_size.state) == pytest.approx(1.5)
    assert total_size.attributes[ATTR_UNIT_OF_MEASUREMENT] == "TB"

    uploaded = _state(hass, "sensor.rustatio_simulated_uploaded")
    assert float(uploaded.state) == pytest.approx(2.0)
    assert uploaded.attributes[ATTR_UNIT_OF_MEASUREMENT] == "GB"

    downloaded = _state(hass, "sensor.rustatio_simulated_downloaded")
    assert float(downloaded.state) == pytest.approx(1.0)
    assert downloaded.attributes[ATTR_UNIT_OF_MEASUREMENT] == "GB"

    connected = _state(hass, "binary_sensor.rustatio_connected")
    assert connected.state == STATE_ON


async def test_entities_become_unavailable_and_recover(
    hass: HomeAssistant,
    setup_rustatio: MockConfigEntry,
    mock_rustatio_api: MockRustatioApi,
) -> None:
    """Test availability behavior when Rustatio disappears and returns."""
    mock_rustatio_api.summaries.side_effect = RustatioConnectionError("offline")

    await setup_rustatio.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert (
        _state(hass, "sensor.rustatio_managed_torrents").state
        == STATE_UNAVAILABLE
    )
    assert _state(hass, "binary_sensor.rustatio_connected").state == STATE_OFF

    mock_rustatio_api.summaries.side_effect = None
    mock_rustatio_api.summaries.return_value = INSTANCE_SUMMARIES

    await setup_rustatio.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert _state(hass, "sensor.rustatio_managed_torrents").state == "3"
    assert _state(hass, "binary_sensor.rustatio_connected").state == STATE_ON


async def test_unload_config_entry(
    hass: HomeAssistant,
    setup_rustatio: MockConfigEntry,
) -> None:
    """Test that the Rustatio config entry unloads cleanly."""
    assert await hass.config_entries.async_unload(setup_rustatio.entry_id)
    await hass.async_block_till_done()

    assert setup_rustatio.state is ConfigEntryState.NOT_LOADED

    # HA may retain restored unavailable states after an entity platform unload.
    # Their presence is therefore not evidence that the config entry failed
    # to unload.
    managed = hass.states.get("sensor.rustatio_managed_torrents")
    if managed is not None:
        assert managed.state == STATE_UNAVAILABLE
        assert managed.attributes.get("restored") is True
