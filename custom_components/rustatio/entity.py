"""Common Rustatio entity helpers."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RustatioCoordinator


class RustatioEntity(CoordinatorEntity[RustatioCoordinator]):
    """Base entity shared by all Rustatio entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RustatioCoordinator,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            name="Rustatio",
            manufacturer="r-jean-pierre",
            model="Rustatio Home Assistant integration",
        )
