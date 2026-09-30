"""Data coordinator for Rustatio."""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RustatioApi, RustatioAuthError, RustatioError
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RustatioData:
    """Aggregated Rustatio statistics exposed to Home Assistant.

    Rustatio calls a managed torrent an "instance" internally. The coordinator
    converts that upstream terminology into user-facing Home Assistant terms.
    """

    managed_torrents: int
    running_torrents: int
    torrent_states: dict[str, int]
    torrent_sources: dict[str, int]

    total_torrent_size: int
    uploaded: int
    downloaded: int
    upload_rate: float
    download_rate: float
    torrents_with_tracker_errors: int

    watch_enabled: bool
    watch_folder: str
    watch_auto_start: bool
    torrent_files: int
    loaded_torrent_files: int


class RustatioCoordinator(DataUpdateCoordinator[RustatioData]):
    """Poll Rustatio once and share the result with every entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: RustatioApi,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
            always_update=False,
        )
        self.api = api

    async def _async_update_data(self) -> RustatioData:
        """Fetch and aggregate the two Rustatio API resources we use."""
        try:
            summaries, watch = await asyncio.gather(
                self.api.async_get_instance_summaries(),
                self.api.async_get_watch_status(),
            )
        except RustatioAuthError as err:
            raise ConfigEntryAuthFailed("Rustatio authentication failed") from err
        except RustatioError as err:
            raise UpdateFailed(str(err)) from err

        states = Counter(
            str(item.get("state", "unknown")).lower() for item in summaries
        )
        sources = Counter(
            str(item.get("source", "unknown")).lower() for item in summaries
        )

        return RustatioData(
            managed_torrents=len(summaries),
            running_torrents=states.get("running", 0),
            torrent_states=dict(states),
            torrent_sources=dict(sources),
            total_torrent_size=_sum_int(summaries, "totalSize"),
            uploaded=_sum_int(summaries, "uploaded"),
            downloaded=_sum_int(summaries, "downloaded"),
            upload_rate=_sum_float(summaries, "currentUploadRate"),
            download_rate=_sum_float(summaries, "currentDownloadRate"),
            torrents_with_tracker_errors=sum(
                1
                for item in summaries
                if item.get("trackerError") is not None
                or item.get("isTrackerInvalid") is True
            ),
            watch_enabled=bool(watch.get("enabled", False)),
            watch_folder=str(watch.get("watch_dir", "")),
            watch_auto_start=bool(watch.get("auto_start", False)),
            torrent_files=_as_int(watch.get("file_count")),
            loaded_torrent_files=_as_int(watch.get("loaded_count")),
        )


def _as_int(value: Any) -> int:
    """Convert a numeric API value to int without accepting booleans."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _as_float(value: Any) -> float:
    """Convert a numeric API value to float without accepting booleans."""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _sum_int(items: list[dict[str, Any]], key: str) -> int:
    """Sum an integer field from Rustatio summaries."""
    return sum(_as_int(item.get(key)) for item in items)


def _sum_float(items: list[dict[str, Any]], key: str) -> float:
    """Sum a floating-point field from Rustatio summaries."""
    return sum(_as_float(item.get(key)) for item in items)
