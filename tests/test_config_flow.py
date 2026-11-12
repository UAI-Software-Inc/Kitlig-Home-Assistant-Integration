"""Adding an instance: by hand, from discovery, twice, and signing in again."""

from __future__ import annotations

from ipaddress import ip_address

from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from custom_components.kitlig.const import DOMAIN

from .conftest import Server, make_entry
from .fake_kitlig import PASSWORD


async def _user_flow(hass: HomeAssistant, server: Server, password: str = PASSWORD):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": server.host, "port": server.port, "password": password}
    )


async def test_user_flow_stores_token_not_password(hass: HomeAssistant, kitlig: Server) -> None:
    result = await _user_flow(hass, kitlig)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Studio"
    assert result["data"]["token"] == "tok_Studio_1"
    assert result["data"]["server_id"] == "srv_1"
    assert PASSWORD not in str(result["data"])
    assert result["result"].unique_id == "srv_1"
    await hass.config_entries.async_unload(result["result"].entry_id)


async def test_wrong_password_then_right(hass: HomeAssistant, kitlig: Server) -> None:
    result = await _user_flow(hass, kitlig, "nope")
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": kitlig.host, "port": kitlig.port, "password": PASSWORD}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.config_entries.async_unload(result["result"].entry_id)


async def test_errors(hass: HomeAssistant, kitlig: Server) -> None:
    kitlig.fake.web_on = False
    result = await _user_flow(hass, kitlig)
    assert result["errors"] == {"base": "web_off"}

    kitlig.fake.web_on = True
    kitlig.fake.tokens = {f"t{i}" for i in range(10)}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": kitlig.host, "port": kitlig.port, "password": PASSWORD}
    )
    assert result["errors"] == {"base": "device_cap"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": kitlig.host, "port": 1, "password": PASSWORD}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_same_instance_twice_aborts(hass: HomeAssistant, kitlig: Server) -> None:
    make_entry(kitlig).add_to_hass(hass)
    result = await _user_flow(hass, kitlig)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_no_server_id_falls_back_to_address(hass: HomeAssistant, start_kitlig) -> None:
    server = await start_kitlig("Old Build", None)
    result = await _user_flow(hass, server)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == f"127.0.0.1:{server.port}"
    await hass.config_entries.async_unload(result["result"].entry_id)


def _discovery(server: Server, server_id: str = "srv_1") -> ZeroconfServiceInfo:
    return ZeroconfServiceInfo(
        ip_address=ip_address(server.host),
        ip_addresses=[ip_address(server.host)],
        hostname="studio.local.",
        name="Studio._kitlig._tcp.local.",
        port=server.port,
        properties={"id": server_id, "name": "Studio", "version": "0.14.1"},
        type="_kitlig._tcp.local.",
    )


async def test_discovery(hass: HomeAssistant, kitlig: Server) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_discovery(kitlig)
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": PASSWORD})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["port"] == kitlig.port
    await hass.config_entries.async_unload(result["result"].entry_id)


async def test_discovery_of_known_instance_updates_address(hass: HomeAssistant, kitlig: Server) -> None:
    entry = make_entry(kitlig)
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, data={**entry.data, "port": 9999})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_discovery(kitlig)
    )
    assert result["type"] is FlowResultType.ABORT
    assert entry.data["port"] == kitlig.port
    await hass.async_block_till_done()
    await hass.config_entries.async_unload(entry.entry_id)


async def test_reauth(hass: HomeAssistant, kitlig: Server) -> None:
    entry = make_entry(kitlig, token="tok_revoked")
    kitlig.fake.tokens.clear()
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": PASSWORD})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["token"] == "tok_Studio_1"
    await hass.async_block_till_done()
    await hass.config_entries.async_unload(entry.entry_id)
