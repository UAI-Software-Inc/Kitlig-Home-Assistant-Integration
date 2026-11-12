# Development

This page is for people changing the integration.

## Layout

```text
custom_components/kitlig/
  __init__.py        setup, the card, the media proxy, actions
  api.py             the Kitlig Web client
  coordinator.py     one per instance: state, live events, the regular check
  config_flow.py     add, discover, sign in again, reconfigure, options
  entity.py          base entity and device info
  sensor.py  binary_sensor.py  button.py  image.py  event.py
  media_source.py    the media browser
  views.py           passes files and thumbnails through Home Assistant
  websocket.py       data for the card
  device_trigger.py  device triggers
  diagnostics.py     the diagnostics download
  frontend/kitlig-card.js   the dashboard card, plain JavaScript with no build step
  brand/             the logo Home Assistant shows
  translations/en.json      every user-facing string
tests/               the test suite and a fake Kitlig server
docs/                this site
```

## How it talks to Kitlig

The integration uses **Kitlig Web**, the REST and server-sent-events API that Kitlig serves on its server port next to `/mcp`. The contract is `docs/api/kitlig-web.openapi.yaml` in the Kitlig repository.

| Route | Used for |
|---|---|
| `POST /api/login` | Trading the password for a device token. |
| `POST /api/logout` | Freeing the device slot when an instance is removed. |
| `GET /api/me` | Version, name, server ID and the open project. |
| `GET /api/jobs` | The job list. |
| `POST /api/jobs/{id}/cancel`, `/retry` | Job control. |
| `GET /api/assets`, `/api/assets/{id}` | Media listings and one file's details. |
| `GET /api/assets/{id}/thumb`, `/file` | Thumbnails and file bytes. |
| `GET /api/sites`, `/api/sites/{id}/view` | Sites and games, and a link to open one. |
| `GET /api/review/sequences` | Review status per sequence. |
| `GET /api/spend` | The open project's spend per period. |
| `GET /api/events` | The live stream. |

Every write sends the header `X-Kitlig-Web: 1`. Discovery uses the mDNS service `_kitlig._tcp` with the TXT keys `id`, `name` and `version`.

### Keeping state current

`KitligCoordinator` holds one immutable `KitligData` per instance.

- **Live events** patch it. A `job` event updates one job. `assets`, `comments`, `sites` and `project` events mark a slice as stale and ask for a refresh.
- **The regular check** reads `/api/me` and the jobs every time, and the slower slices (sites, reviews, latest media, spend) only when they are stale or five minutes have passed.
- **A change of project** makes every slice stale, whether it was seen by an event or by the check.
- **A check that races with an event** is thrown away and run again, so older data never overwrites a newer event.

Job events for automations are raised in `_note_job`, which compares each job's status with the last one seen. Nothing fires until the first full read, so a restart does not replay old jobs.

## Run the tests

Home Assistant needs Python 3.13 or newer.

```bash
pip install -r requirements_test.txt
```

```bash
pytest
```

The tests start `tests/fake_kitlig.py`, a small server that speaks the same routes, and run the real integration against it over a local socket. That covers the setup flows, every entity, live events, the media browser and proxy, the card's data, actions, and two instances side by side.

When you add a route to the client, add it to the fake server too.

## Lint

```bash
ruff check custom_components tests
```

## Try it in Home Assistant

Copy `custom_components/kitlig` into a Home Assistant configuration folder and restart. Python changes need a restart. Changes to `kitlig-card.js` only need a browser refresh, because the file is served without caching.

## Build these docs

```bash
pip install -r requirements_docs.txt
```

```bash
mkdocs serve
```

That serves the site at `http://127.0.0.1:8000` and rebuilds as you edit. To build it the way the deploy does:

```bash
mkdocs build --strict
```

`--strict` turns broken links and missing pages into errors.

### Deploying

`.github/workflows/release-docs.yml` builds the site on every push and pull request. On a push to `main` it also publishes the result to GitHub Pages.

The repository needs one setting for that to work: **Settings ▸ Pages ▸ Build and deployment ▸ Source** set to **GitHub Actions**.

## Release a version

1. Set the new version in `custom_components/kitlig/manifest.json` and in `VERSION` in `custom_components/kitlig/const.py`. The card's address includes the version, so browsers fetch the new card.
2. Run the tests.
3. Commit, then create a GitHub release with a tag such as `v0.2.0`. HACS offers tagged releases to users.

## Conventions

- Every string a user sees lives in `translations/en.json`.
- Entity IDs come from `translation_key`, so renaming a key changes entity IDs for new installs. Avoid it.
- The integration stores the device token only. Do not store or log the password.
- Kitlig hands out IDs, never file paths. Keep it that way in anything the integration exposes.
