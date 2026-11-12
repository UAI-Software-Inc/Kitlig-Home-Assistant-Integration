"""Base entity: every entity of an instance hangs off that instance's one device."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KitligCoordinator


class KitligEntity(CoordinatorEntity[KitligCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: KitligCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="UAI Software",
            model="Kitlig",
            sw_version=coordinator.data.me.get("version"),
            configuration_url=coordinator.client.base_url,
            entry_type=DeviceEntryType.SERVICE,
        )
