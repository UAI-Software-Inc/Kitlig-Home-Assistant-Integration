"""Adding a Kitlig instance: by hand, from network discovery, and signing in again."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import (
    KitligAuthError,
    KitligClient,
    KitligConnectionError,
    KitligDeviceCapError,
    KitligError,
    KitligRateLimitError,
    KitligWebOffError,
)
from .const import (
    CONF_BROWSER_URL,
    CONF_READ_ONLY,
    CONF_SERVER_ID,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_NAME,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

PASSWORD_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)


def _user_schema(host: str = "", port: int = DEFAULT_PORT) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=host): str,
            vol.Required(CONF_PORT, default=port): cv.port,
            vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
        }
    )


PASSWORD_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR})


class KitligConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kitlig."""

    VERSION = 1

    def __init__(self) -> None:
        self._host = ""
        self._port = DEFAULT_PORT
        self._name = "Kitlig"

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Any) -> KitligOptionsFlow:
        return KitligOptionsFlow()

    async def _sign_in(
        self, host: str, port: int, password: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Sign in. Returns (login result, None) or (None, error key)."""
        client = KitligClient(async_get_clientsession(self.hass), host, port)
        name = f"{DEVICE_NAME} ({self.hass.config.location_name})"
        try:
            return await client.login(password, name[:80]), None
        except KitligAuthError:
            return None, "invalid_auth"
        except KitligWebOffError:
            return None, "web_off"
        except KitligDeviceCapError:
            return None, "device_cap"
        except KitligRateLimitError:
            return None, "rate_limited"
        except KitligConnectionError:
            return None, "cannot_connect"
        except KitligError:
            return None, "unknown"

    @staticmethod
    def _entry_data(host: str, port: int, login: dict[str, Any]) -> dict[str, Any]:
        return {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_TOKEN: login["token"],
            CONF_SERVER_ID: login.get("serverId"),
            CONF_READ_ONLY: bool(login.get("readOnly")),
        }

    async def _finish(self, host: str, port: int, login: dict[str, Any]) -> ConfigFlowResult:
        # Older Kitlig builds have no serverId; the address then stands in for the identity.
        unique_id = login.get("serverId") or f"{host}:{port}"
        await self.async_set_unique_id(unique_id, raise_on_progress=False)
        data = self._entry_data(host, port, login)
        self._abort_if_unique_id_configured(updates=data)
        return self.async_create_entry(title=login.get("serverName") or host, data=data)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            login, error = await self._sign_in(host, port, user_input[CONF_PASSWORD])
            if login is not None:
                return await self._finish(host, port, login)
            errors["base"] = error or "unknown"
            self._host, self._port = host, port
        return self.async_show_form(
            step_id="user", data_schema=_user_schema(self._host, self._port), errors=errors
        )

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        self._host = str(discovery_info.host)
        self._port = discovery_info.port or DEFAULT_PORT
        props = discovery_info.properties
        self._name = props.get("name") or discovery_info.name.split(".")[0]
        if server_id := props.get("id"):
            await self.async_set_unique_id(server_id)
            self._abort_if_unique_id_configured(
                updates={CONF_HOST: self._host, CONF_PORT: self._port}
            )
        else:
            self._async_abort_entries_match({CONF_HOST: self._host, CONF_PORT: self._port})
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            login, error = await self._sign_in(self._host, self._port, user_input[CONF_PASSWORD])
            if login is not None:
                return await self._finish(self._host, self._port, login)
            errors["base"] = error or "unknown"
        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=PASSWORD_SCHEMA,
            errors=errors,
            description_placeholders={"name": self._name, "host": self._host},
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host, port = entry.data[CONF_HOST], entry.data[CONF_PORT]
            login, error = await self._sign_in(host, port, user_input[CONF_PASSWORD])
            if login is not None:
                return self.async_update_reload_and_abort(
                    entry, data_updates=self._entry_data(host, port, login)
                )
            errors["base"] = error or "unknown"
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=PASSWORD_SCHEMA,
            errors=errors,
            description_placeholders={"name": entry.title},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The instance moved to another address."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            login, error = await self._sign_in(host, port, user_input[CONF_PASSWORD])
            if login is not None:
                server_id = login.get("serverId")
                if server_id and entry.data.get(CONF_SERVER_ID) not in (None, server_id):
                    errors["base"] = "wrong_instance"
                else:
                    return self.async_update_reload_and_abort(
                        entry, data_updates=self._entry_data(host, port, login)
                    )
            else:
                errors["base"] = error or "unknown"
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_user_schema(entry.data[CONF_HOST], entry.data[CONF_PORT]),
            errors=errors,
        )


class KitligOptionsFlow(OptionsFlow):
    """Options for one instance."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=3600)),
                vol.Optional(
                    CONF_BROWSER_URL,
                    description={"suggested_value": options.get(CONF_BROWSER_URL, "")},
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
