"""The integration against a fake Kitlig: entities, live events, actions, media, two instances."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from homeassistant.components.media_source import async_browse_media, async_resolve_media
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.kitlig.const import DOMAIN, EVENT_JOB

from .conftest import Server, make_entry, setup_entry, wait_for
from .fake_kitlig import FILE_BYTES, THUMB_BYTES, job


def state(hass: HomeAssistant, entity_id: str) -> str:
    found = hass.states.get(entity_id)
    assert found is not None, f"{entity_id} does not exist"
    return found.state


async def test_entities(hass: HomeAssistant, loaded: MockConfigEntry) -> None:
    assert state(hass, "sensor.studio_jobs_running") == "1"
    assert state(hass, "sensor.studio_jobs_queued") == "1"
    assert state(hass, "sensor.studio_current_job") == "Image to Video"
    assert state(hass, "sensor.studio_current_job_progress") == "50"
    assert state(hass, "sensor.studio_open_project") == "Launch Film"
    assert state(hass, "sensor.studio_open_review_comments") == "4"
    assert state(hass, "sensor.studio_sites") == "1"
    assert state(hass, "sensor.studio_games") == "1"
    assert state(hass, "sensor.studio_version") == "0.14.0"
    assert state(hass, "binary_sensor.studio_connected") == "on"
    assert state(hass, "binary_sensor.studio_working") == "on"
    assert state(hass, "binary_sensor.studio_needs_answer") == "off"

    running = hass.states.get("sensor.studio_jobs_running").attributes["jobs"]
    assert running == [
        {
            "job_id": "job_2",
            "label": "Image to Video",
            "status": "running",
            "progress": 50,
            "phase": "render",
            "message": "Rendering",
            "started": "2026-11-12T10:00:02.000Z",
        }
    ]
    review = hass.states.get("sensor.studio_open_review_comments").attributes["sequences"]
    assert review[0]["latest_export"] == "Main Cut.mp4"
    assert (review[0]["favorites"], review[0]["rating"], review[0]["rating_count"]) == (2, 4.5, 3)
    games = hass.states.get("sensor.studio_games").attributes["items"]
    assert games[0]["site_id"] == "site_g"

    device = dr.async_entries_for_config_entry(dr.async_get(hass), loaded.entry_id)[0]
    assert device is not None and device.name == "Studio" and device.sw_version == "0.14.0"


async def test_project_spend(hass: HomeAssistant, kitlig: Server, loaded: MockConfigEntry) -> None:
    spend = hass.states.get("sensor.studio_project_spend")
    assert spend.state == "12.3456"
    assert spend.attributes["unit_of_measurement"] == "USD"
    assert spend.attributes["today"] == 0.5
    assert spend.attributes["this_month"] == 4.5
    assert spend.attributes["unpriced_runs"] == 2

    # A finished job is what changes the total.
    kitlig.fake.spend_usd = 13.0
    kitlig.fake.set_job("job_2", "complete")
    await wait_for(lambda: state(hass, "sensor.studio_project_spend") == "13.0")

    kitlig.fake.project = None
    kitlig.fake.push({"type": "project", "project": None})
    await wait_for(lambda: state(hass, "sensor.studio_project_spend") == "unknown")


async def test_kitlig_without_spend_route(hass: HomeAssistant, kitlig: Server) -> None:
    kitlig.fake.has_spend = False
    entry = make_entry(kitlig)
    await setup_entry(hass, entry)
    assert state(hass, "sensor.studio_project_spend") == "unknown"
    assert state(hass, "sensor.studio_jobs_running") == "1"
    await hass.config_entries.async_unload(entry.entry_id)


async def test_project_opened_while_stream_was_down(hass: HomeAssistant, kitlig: Server) -> None:
    """Kitlig restarts with no project, then opens one before the event stream is back."""
    kitlig.fake.project = None
    entry = make_entry(kitlig, scan_interval=10)
    await setup_entry(hass, entry)
    assert state(hass, "sensor.studio_sites") == "0"
    assert state(hass, "sensor.studio_project_spend") == "unknown"

    kitlig.fake.project = {"projectId": "proj_1", "name": "Launch Film"}  # no event sent
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert state(hass, "sensor.studio_open_project") == "Launch Film"
    assert state(hass, "sensor.studio_sites") == "1"
    assert state(hass, "sensor.studio_games") == "1"
    assert state(hass, "sensor.studio_project_spend") == "12.3456"
    assert hass.states.get("image.studio_latest_media").attributes["name"] == "hero.png"
    await hass.config_entries.async_unload(entry.entry_id)


async def test_live_job_events(hass: HomeAssistant, kitlig: Server, loaded: MockConfigEntry) -> None:
    events = async_capture_events(hass, EVENT_JOB)

    kitlig.fake.set_job("job_2", "running", progress={"phase": "render", "pct": 0.9})
    await wait_for(lambda: state(hass, "sensor.studio_current_job_progress") == "90")
    assert events == []

    kitlig.fake.set_job("job_2", "complete", outputs=[{"assetId": "asset_new", "kind": "video"}])
    await wait_for(lambda: state(hass, "sensor.studio_jobs_running") == "0")
    await hass.async_block_till_done()
    assert state(hass, "binary_sensor.studio_working") == "off"
    assert len(events) == 1
    data = events[0].data
    assert data["type"] == "finished"
    assert data["job_id"] == "job_2"
    assert data["outputs"] == ["asset_new"]
    assert data["config_entry_id"] == loaded.entry_id
    device = dr.async_entries_for_config_entry(dr.async_get(hass), loaded.entry_id)[0]
    assert data["device_id"] == device.id
    assert hass.states.get("event.studio_job").attributes["event_type"] == "finished"

    kitlig.fake.set_job("job_1", "awaiting-input")
    await wait_for(lambda: state(hass, "binary_sensor.studio_needs_answer") == "on")
    assert events[-1].data["type"] == "needs_answer"


async def test_new_job_and_project_change(hass: HomeAssistant, kitlig: Server, loaded: MockConfigEntry) -> None:
    kitlig.fake.jobs.insert(0, job("job_9", "running", "Remove Background"))
    kitlig.fake.push({"type": "job", "job": kitlig.fake.jobs[0]})
    await wait_for(lambda: state(hass, "sensor.studio_jobs_running") == "2")
    assert state(hass, "sensor.studio_current_job") == "Remove Background"

    kitlig.fake.project = None
    kitlig.fake.push({"type": "project", "project": None})
    await wait_for(lambda: state(hass, "sensor.studio_sites") == "0")
    assert state(hass, "sensor.studio_jobs_running") == "0"
    assert state(hass, "sensor.studio_open_project") == "unknown"
    assert state(hass, "binary_sensor.studio_connected") == "on"


async def test_buttons_and_actions(hass: HomeAssistant, kitlig: Server, loaded: MockConfigEntry) -> None:
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.studio_cancel_running_jobs"}, blocking=True
    )
    assert sorted(kitlig.fake.cancelled) == ["job_1", "job_2"]
    assert state(hass, "sensor.studio_jobs_running") == "0"

    await hass.services.async_call(
        "button", "press", {"entity_id": "button.studio_retry_last_failed_job"}, blocking=True
    )
    assert kitlig.fake.retried == ["job_0"]

    await hass.services.async_call(DOMAIN, "retry_job", {"job_id": "job_2"}, blocking=True)
    assert kitlig.fake.retried == ["job_0", "job_2"]

    result = await hass.services.async_call(
        DOMAIN,
        "get_site_url",
        {"site_id": "site_g", "page": "index.html?scene=scene.json"},
        blocking=True,
        return_response=True,
    )
    assert result["url"] == (
        f"http://127.0.0.1:{kitlig.port}/view/viewtoken/boltway/index.html?scene=scene.json"
    )


async def test_browser_url_option(hass: HomeAssistant, kitlig: Server) -> None:
    entry = make_entry(kitlig, browser_url="https://kitlig.example.com/")
    await setup_entry(hass, entry)
    result = await entry.runtime_data.site_url("site_a")
    assert result["url"] == "https://kitlig.example.com/view/viewtoken/landing/"
    await hass.config_entries.async_unload(entry.entry_id)


async def test_read_only_instance_has_no_buttons(hass: HomeAssistant, kitlig: Server) -> None:
    kitlig.fake.read_only = True
    entry = make_entry(kitlig)
    await setup_entry(hass, entry)
    assert hass.states.get("button.studio_cancel_running_jobs") is None
    assert state(hass, "sensor.studio_jobs_running") == "1"
    await hass.config_entries.async_unload(entry.entry_id)


async def test_media_browser(hass: HomeAssistant, kitlig: Server, loaded: MockConfigEntry, hass_client) -> None:
    root = await async_browse_media(hass, f"media-source://{DOMAIN}")
    assert [c.title for c in root.children] == ["Recent", "Videos", "Images", "Audio", "Exports"]

    exports = await async_browse_media(hass, f"media-source://{DOMAIN}/{loaded.entry_id}/exports")
    assert [c.title for c in exports.children] == ["Main Cut.mp4"]
    child = exports.children[0]
    assert child.media_content_type == "video/mp4"
    assert f"/api/kitlig/{loaded.entry_id}/asset/asset_exp/thumb?authSig=" in child.thumbnail

    recent = await async_browse_media(hass, f"media-source://{DOMAIN}/{loaded.entry_id}/recent")
    assert "notes.md" not in [c.title for c in recent.children]

    play = await async_resolve_media(
        hass, f"media-source://{DOMAIN}/{loaded.entry_id}/exports/asset_exp", None
    )
    assert play.mime_type == "video/mp4"
    assert play.url == f"/api/kitlig/{loaded.entry_id}/asset/asset_exp/file/Main%20Cut.mp4"

    client = await hass_client()
    whole = await client.get(play.url)
    assert whole.status == HTTPStatus.OK
    assert await whole.read() == FILE_BYTES

    part = await client.get(play.url, headers={"Range": "bytes=10-19"})
    assert part.status == HTTPStatus.PARTIAL_CONTENT
    assert part.headers["Content-Range"] == "bytes 10-19/1024"
    assert await part.read() == FILE_BYTES[10:20]
    assert kitlig.fake.ranges[-1] == "bytes=10-19"

    thumb = await client.get(f"/api/kitlig/{loaded.entry_id}/asset/asset_exp/thumb")
    assert await thumb.read() == THUMB_BYTES

    assert (await client.get("/api/kitlig/nope/asset/asset_exp/file")).status == HTTPStatus.NOT_FOUND


async def test_media_needs_sign_in(hass: HomeAssistant, loaded: MockConfigEntry, hass_client_no_auth) -> None:
    client = await hass_client_no_auth()
    response = await client.get(f"/api/kitlig/{loaded.entry_id}/asset/asset_exp/file")
    assert response.status == HTTPStatus.UNAUTHORIZED


async def test_latest_media_image(hass: HomeAssistant, loaded: MockConfigEntry, hass_client) -> None:
    attributes = hass.states.get("image.studio_latest_media").attributes
    assert attributes["name"] == "hero.png"
    client = await hass_client()
    response = await client.get("/api/image_proxy/image.studio_latest_media")
    assert response.status == HTTPStatus.OK
    assert await response.read() == THUMB_BYTES


async def test_card_data(hass: HomeAssistant, kitlig: Server, loaded: MockConfigEntry, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "kitlig/instances"})
    message = await client.receive_json()
    assert message["success"]
    (instance,) = message["result"]["instances"]
    assert instance["name"] == "Studio"
    assert instance["jobs_running"] == 1
    assert instance["current_job"]["progress"] == 50
    assert [s["kind"] for s in instance["sites"]] == ["site", "game"]

    await client.send_json_auto_id(
        {"type": "kitlig/site_url", "entry_id": loaded.entry_id, "site_id": "site_a"}
    )
    message = await client.receive_json()
    assert message["result"]["url"] == f"http://127.0.0.1:{kitlig.port}/view/viewtoken/landing/"

    await client.send_json_auto_id(
        {"type": "kitlig/site_url", "entry_id": loaded.entry_id, "site_id": "missing"}
    )
    message = await client.receive_json()
    assert not message["success"]


async def test_two_instances_stay_separate(hass: HomeAssistant, start_kitlig) -> None:
    studio = await start_kitlig("Studio", "srv_1")
    render = await start_kitlig("Render Box", "srv_2")
    render.fake.jobs = [job("job_7", "running", "Export"), job("job_8", "running", "Upscale")]
    render.fake.sites = []
    first, second = make_entry(studio, "tok_a"), make_entry(render, "tok_b")
    await setup_entry(hass, first)
    await setup_entry(hass, second)
    await wait_for(lambda: studio.fake.stream_count == 1 and render.fake.stream_count == 1)

    assert state(hass, "sensor.studio_jobs_running") == "1"
    assert state(hass, "sensor.render_box_jobs_running") == "2"
    assert state(hass, "sensor.render_box_sites") == "0"

    render.fake.set_job("job_7", "complete")
    await wait_for(lambda: state(hass, "sensor.render_box_jobs_running") == "1")
    assert state(hass, "sensor.studio_jobs_running") == "1"

    root = await async_browse_media(hass, f"media-source://{DOMAIN}")
    assert [c.title for c in root.children] == ["Studio (Launch Film)", "Render Box (Launch Film)"]

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "cancel_job", {"job_id": "job_8"}, blocking=True)
    await hass.services.async_call(
        DOMAIN, "cancel_job", {"config_entry_id": second.entry_id, "job_id": "job_8"}, blocking=True
    )
    assert render.fake.cancelled == ["job_8"] and studio.fake.cancelled == []

    for entry in (first, second):
        await hass.config_entries.async_unload(entry.entry_id)


async def test_revoked_token_asks_to_sign_in_again(hass: HomeAssistant, kitlig: Server) -> None:
    entry = make_entry(kitlig)
    kitlig.fake.tokens.clear()
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert any(flow["context"]["source"] == "reauth" for flow in hass.config_entries.flow.async_progress())


async def test_unreachable_instance_retries(hass: HomeAssistant, kitlig: Server) -> None:
    entry = make_entry(kitlig)
    entry.add_to_hass(hass)
    await kitlig.runner.cleanup()
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    await hass.config_entries.async_unload(entry.entry_id)


async def test_removing_the_entry_signs_out(hass: HomeAssistant, kitlig: Server, loaded: MockConfigEntry) -> None:
    assert "tok_preset" in kitlig.fake.tokens
    await hass.config_entries.async_remove(loaded.entry_id)
    await hass.async_block_till_done()
    assert "tok_preset" not in kitlig.fake.tokens
