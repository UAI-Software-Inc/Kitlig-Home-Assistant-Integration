"""Shared fixtures: fake Kitlig servers and config entries that point at them."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import pytest
from aiohttp import web
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kitlig.const import CONF_READ_ONLY, CONF_SERVER_ID, DOMAIN

from .fake_kitlig import FakeKitlig

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load the integration under test."""


class Server:
    """A running fake Kitlig."""

    def __init__(self, fake: FakeKitlig, runner: web.AppRunner, port: int) -> None:
        self.fake = fake
        self.runner = runner
        self.port = port
        self.host = "127.0.0.1"


@pytest.fixture
async def start_kitlig(socket_enabled: None) -> AsyncIterator[Callable[..., Awaitable[Server]]]:
    servers: list[Server] = []

    async def start(name: str = "Studio", server_id: str | None = "srv_1") -> Server:
        fake = FakeKitlig(name, server_id)
        runner = web.AppRunner(fake.app())
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        server = Server(fake, runner, port)
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.fake.close_streams()
        await server.runner.cleanup()


@pytest.fixture
async def kitlig(start_kitlig: Callable[..., Awaitable[Server]]) -> Server:
    return await start_kitlig()


def make_entry(server: Server, token: str = "tok_preset", **options: Any) -> MockConfigEntry:
    server.fake.tokens.add(token)
    return MockConfigEntry(
        domain=DOMAIN,
        title=server.fake.name,
        unique_id=server.fake.server_id or f"{server.host}:{server.port}",
        data={
            "host": server.host,
            "port": server.port,
            "token": token,
            CONF_SERVER_ID: server.fake.server_id,
            CONF_READ_ONLY: False,
        },
        options=options,
    )


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def wait_for(condition: Callable[[], bool], timeout: float = 5.0) -> None:
    """Wait for something that arrives over a real socket."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not condition():
        if loop.time() > deadline:
            raise AssertionError("Timed out waiting for the condition")
        await asyncio.sleep(0.02)


@pytest.fixture
async def loaded(hass: HomeAssistant, kitlig: Server) -> AsyncIterator[MockConfigEntry]:
    """One instance, set up, with its event stream connected."""
    entry = make_entry(kitlig)
    await setup_entry(hass, entry)
    await wait_for(lambda: kitlig.fake.stream_count == 1)
    yield entry
    if hass.config_entries.async_get_entry(entry.entry_id) is not None:
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
