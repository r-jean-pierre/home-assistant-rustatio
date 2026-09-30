"""Aggregate sensors for Rustatio."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfDataRate, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RustatioConfigEntry
from .coordinator import RustatioCoordinator, RustatioData
from .entity import RustatioEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class RustatioSensorDescription(SensorEntityDescription):
    """Describe one aggregate Rustatio sensor."""

    value_fn: Callable[[RustatioData], int | float]


SENSORS: tuple[RustatioSensorDescription, ...] = (
    RustatioSensorDescription(
        key="managed_torrents",
        translation_key="managed_torrents",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.managed_torrents,
    ),
    RustatioSensorDescription(
        key="running_torrents",
        translation_key="running_torrents",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.running_torrents,
    ),
    RustatioSensorDescription(
        key="torrents_with_tracker_errors",
        translation_key="torrents_with_tracker_errors",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.torrents_with_tracker_errors,
    ),
    RustatioSensorDescription(
        key="torrent_files",
        translation_key="torrent_files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.torrent_files,
    ),
    RustatioSensorDescription(
        key="upload_rate",
        translation_key="upload_rate",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.upload_rate,
    ),
    RustatioSensorDescription(
        key="download_rate",
        translation_key="download_rate",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.download_rate,
    ),
    RustatioSensorDescription(
        key="total_torrent_size",
        translation_key="total_torrent_size",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.TERABYTES,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.total_torrent_size,
    ),
    RustatioSensorDescription(
        key="uploaded",
        translation_key="uploaded",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.uploaded,
    ),
    RustatioSensorDescription(
        key="downloaded",
        translation_key="downloaded",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.downloaded,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RustatioConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Rustatio sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        RustatioSensor(coordinator, entry.entry_id, description)
        for description in SENSORS
    )


class RustatioSensor(RustatioEntity, SensorEntity):
    """Representation of an aggregate Rustatio sensor."""

    entity_description: RustatioSensorDescription

    def __init__(
        self,
        coordinator: RustatioCoordinator,
        entry_id: str,
        description: RustatioSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> int | float:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Expose compact context without creating per-torrent entities."""
        data = self.coordinator.data

        if self.entity_description.key == "managed_torrents":
            return {
                "torrent_states": data.torrent_states,
                "torrent_sources": data.torrent_sources,
            }

        if self.entity_description.key == "torrent_files":
            return {
                "loaded_torrent_files": data.loaded_torrent_files,
                "watch_enabled": data.watch_enabled,
                "watch_folder": data.watch_folder,
                "auto_start": data.watch_auto_start,
            }

        return None
