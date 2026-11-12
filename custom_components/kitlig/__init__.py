"""Kitlig: watch a Kitlig instance's jobs, media, reviews, sites and games from Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .api import KitligError
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_JOB_ID,
    ATTR_PAGE,
    ATTR_SITE_ID,
    CARD_URL,
    DOMAIN,
    SERVICE_CANCEL_JOB,
    SERVICE_GET_SITE_URL,
    SERVICE_RETRY_JOB,
    VERSION,
)
from .coordinator import KitligConfigEntry, KitligCoordinator
from .views import KitligAssetView
from .websocket import async_register_websocket

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.IMAGE,
    Platform.SENSOR,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

JOB_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string, vol.Required(ATTR_JOB_ID): cv.string}
)
SITE_URL_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_SITE_ID): cv.string,
        vol.Optional(ATTR_PAGE): cv.string,
    }
)


def async_loaded_coordinators(hass: HomeAssistant) -> list[KitligCoordinator]:
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


def async_get_coordinator(hass: HomeAssistant, entry_id: str | None) -> KitligCoordinator:
    """The coordinator an action or card request is about. Without an id, the only instance."""
    coordinators = async_loaded_coordinators(hass)
    if entry_id is None:
        if len(coordinators) == 1:
            return coordinators[0]
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="instance_required" if coordinators else "no_instance",
        )
    for coordinator in coordinators:
        if coordinator.config_entry.entry_id == entry_id:
            return coordinator
    raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_instance")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Things shared by every instance: the card, the media proxy, card data and actions."""
    card = Path(__file__).parent / "frontend" / "kitlig-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card), cache_headers=False)]
    )
    if "frontend" in hass.config.components:
        add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    hass.http.register_view(KitligAssetView())
    async_register_websocket(hass)

    async def cancel_job(call: ServiceCall) -> None:
        coordinator = async_get_coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        try:
            await coordinator.cancel_job(call.data[ATTR_JOB_ID])
        except KitligError as err:
            raise HomeAssistantError(str(err)) from err

    async def retry_job(call: ServiceCall) -> None:
        coordinator = async_get_coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        try:
            await coordinator.retry_job(call.data[ATTR_JOB_ID])
        except KitligError as err:
            raise HomeAssistantError(str(err)) from err

    async def get_site_url(call: ServiceCall) -> ServiceResponse:
        coordinator = async_get_coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        try:
            return await coordinator.site_url(call.data[ATTR_SITE_ID], call.data.get(ATTR_PAGE))
        except KitligError as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(DOMAIN, SERVICE_CANCEL_JOB, cancel_job, schema=JOB_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_RETRY_JOB, retry_job, schema=JOB_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SITE_URL,
        get_site_url,
        schema=SITE_URL_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: KitligConfigEntry) -> bool:
    coordinator = KitligCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_create_background_task(hass, coordinator.listen(), f"kitlig events {entry.title}")
    entry.async_on_unload(entry.add_update_listener(_async_options_changed))
    return True


async def _async_options_changed(hass: HomeAssistant, entry: KitligConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: KitligConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: KitligConfigEntry) -> None:
    """Give the instance its device slot back."""
    from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import KitligClient

    client = KitligClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_TOKEN),
    )
    try:
        await client.logout()
    except KitligError as err:
        _LOGGER.debug("Could not sign out of %s: %s", entry.title, err)
