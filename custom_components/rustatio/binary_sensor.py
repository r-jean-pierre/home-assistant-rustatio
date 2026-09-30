"""Binary sensors for Rustatio."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RustatioConfigEntry
from .coordinator import RustatioCoordinator
from .entity import RustatioEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RustatioConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Rustatio connectivity sensor."""
    async_add_entities(
        [RustatioConnectivitySensor(entry.runtime_data, entry.entry_id)]
    )


class RustatioConnectivitySensor(RustatioEntity, BinarySensorEntity):
    """Show whether the latest Rustatio API refresh succeeded."""

    _attr_translation_key = "connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: RustatioCoordinator,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_connected"

    @property
    def available(self) -> bool:
        """Keep the connectivity entity available so it can report Offline."""
        return True

    @property
    def is_on(self) -> bool:
        """Return true when the last coordinator refresh succeeded."""
        return self.coordinator.last_update_success
