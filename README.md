# Kitlig for Home Assistant

[![Validate](https://github.com/UAI-Software-Inc/Kitlig-Home-Assistant-Integration/actions/workflows/validate.yml/badge.svg)](https://github.com/UAI-Software-Inc/Kitlig-Home-Assistant-Integration/actions/workflows/validate.yml)
[![Docs](https://github.com/UAI-Software-Inc/Kitlig-Home-Assistant-Integration/actions/workflows/release-docs.yml/badge.svg)](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/)

Watch your [Kitlig](https://kitlig.com) instances from Home Assistant. See what each one is working on, get told when a render lands, browse its media and exports, and open its sites and games from a dashboard.

**[Read the documentation](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/)**

## What you get

Add as many Kitlig instances as you have. Each becomes its own device with:

- **Jobs:** running and queued counts, the current job and its progress, and whether a job is waiting for an answer.
- **Job events:** triggers for finished, failed, cancelled and needs-an-answer, for notifications and automations.
- **Project and spend:** the open project and what it has cost so far.
- **Reviews:** open review comments, with each sequence's latest export.
- **Media and exports:** a Kitlig section in the media browser, with thumbnails. Files play through Home Assistant.
- **Sites and games:** a dashboard card that lists them and opens them.
- **Job control:** cancel running jobs and retry a failed one, as buttons and actions.

Everything is local. Home Assistant talks straight to the computer running Kitlig.

## Quick start

1. **Install.** In HACS, add this repository as a custom repository of type **Integration**, download **Kitlig**, and restart Home Assistant. Or copy `custom_components/kitlig` into your `config/custom_components` folder and restart.
2. **Prepare Kitlig.** In Kitlig's **Settings ▸ MCP Server**, turn on the server, **Listen on network** and **Phone companion**. A Docker or headless Kitlig has these on already.
3. **Add it.** In Home Assistant, go to **Settings ▸ Devices & services ▸ Add integration ▸ Kitlig**. Enter the host, port `8420`, and the MCP token or Kitlig Web password.

Repeat step 3 for each Kitlig.

## Documentation

| | |
|---|---|
| [Install](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/getting-started/install/) | HACS and manual install. |
| [Prepare Kitlig](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/getting-started/prepare-kitlig/) | The three settings, the password, and a reachability check. |
| [Add an instance](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/getting-started/add-instance/) | By address or by discovery, and what to do when sign-in fails. |
| [Entities](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/usage/entities/) | Every sensor, button and event, with its attributes. |
| [Media and exports](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/usage/media/) | The media browser and the latest-media image. |
| [Sites and games card](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/usage/card/) | The dashboard card and its options. |
| [Automations](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/usage/automations/) | Ready-to-use examples. |
| [Several instances](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/usage/several-instances/) | How instances are kept apart. |
| [Events](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/reference/events/), [Actions](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/reference/actions/), [Options](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/reference/options/) | Reference. |
| [Troubleshooting](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/troubleshooting/) | Common problems and how to get logs. |
| [Development](https://uai-software-inc.github.io/Kitlig-Home-Assistant-Integration/development/) | Code layout, tests, docs and releases. |

The same pages are in the [`docs`](docs/index.md) folder of this repository.

## Requirements

- Home Assistant 2025.1 or newer.
- Kitlig 0.14.0 or newer. Project spend and automatic discovery need a newer build.

## Development

```bash
pip install -r requirements_test.txt
```

```bash
pytest
```

To preview the documentation:

```bash
pip install -r requirements_docs.txt
```

```bash
mkdocs serve
```

The documentation is built on every push and published to GitHub Pages from `main` by [`release-docs.yml`](.github/workflows/release-docs.yml). See [Development](docs/development.md) for more.

## Problems

Please [open an issue](https://github.com/UAI-Software-Inc/Kitlig-Home-Assistant-Integration/issues), with the diagnostics download and a debug log if you can. [Troubleshooting](docs/troubleshooting.md) explains how to get both.
