"""The newest picture or poster frame of the open project, for a dashboard picture card."""

from __future__ import annotations

from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import KitligError
from .coordinator import KitligConfigEntry, KitligCoordinator
from .entity import KitligEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KitligConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([KitligLatestMedia(hass, entry.runtime_data)])


class KitligLatestMedia(KitligEntity, ImageEntity):
    _attr_content_type = "image/webp"

    def __init__(self, hass: HomeAssistant, coordinator: KitligCoordinator) -> None:
        KitligEntity.__init__(self, coordinator, "latest_media")
        ImageEntity.__init__(self, hass)
        self._shown: tuple[str, int] | None = None
        self._bytes: bytes | None = None
        self._note_latest()

    def _key(self) -> tuple[str, int] | None:
        latest = self.coordinator.data.latest
        return (latest["assetId"], int(latest.get("revision") or 0)) if latest else None

    @callback
    def _note_latest(self) -> None:
        key = self._key()
        if key != self._shown:
            self._shown = key
            self._bytes = None
            self._attr_image_last_updated = dt_util.utcnow() if key else None

    @callback
    def _handle_coordinator_update(self) -> None:
        self._note_latest()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        if self._shown is None:
            return None
        if self._bytes is None:
            try:
                self._bytes, self._attr_content_type = await self.coordinator.client.fetch_thumb(
                    self._shown[0]
                )
            except KitligError:
                return None
        return self._bytes

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        latest = self.coordinator.data.latest
        if not latest:
            return None
        return {
            "asset_id": latest.get("assetId"),
            "name": latest.get("name"),
            "kind": latest.get("kind"),
            "section": latest.get("section"),
            "origin": latest.get("origin"),
            "created": latest.get("createdAt"),
        }
