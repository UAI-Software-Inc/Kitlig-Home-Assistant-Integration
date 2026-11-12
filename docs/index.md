# Kitlig for Home Assistant

This integration puts your [Kitlig](https://kitlig.com) instances in Home Assistant. You can see what each one is working on, get told when a render lands, browse its media and exports, and open its sites and games from a dashboard.

Add as many instances as you have. Each one becomes its own device with its own entities.

## What you get

- **Jobs.** How many are running and queued, the current job and its progress, and whether a job is waiting for you to answer a question.
- **Job events.** Triggers for when a job finishes, fails, is cancelled or needs an answer, so an automation can send a notification or flash a light.
- **Project and spend.** The project open on each Kitlig and what it has cost so far.
- **Reviews.** The number of open review comments, with each sequence's latest export.
- **Media and exports.** A Kitlig section in Home Assistant's media browser, with thumbnails. Files play through Home Assistant.
- **Sites and games.** A dashboard card that lists them and opens them in a new tab.
- **Job control.** Buttons and actions to cancel running jobs and to run a failed job again.

## How it works

Kitlig has a small web API, the same one its phone companion uses. Home Assistant signs in to it once, keeps the device token Kitlig hands back, and then listens to a live stream of changes. A slower check runs alongside as a safety net.

Everything is local. Home Assistant talks straight to the computer running Kitlig, and nothing goes through a cloud service.

!!! note "One project at a time"
    Jobs, media, reviews, spend, sites and games are those of the project that is open on each Kitlig. When someone opens a different project there, the entities follow.

## Start here

1. [Install the integration](getting-started/install.md).
2. [Prepare Kitlig](getting-started/prepare-kitlig.md) so Home Assistant can reach it.
3. [Add an instance](getting-started/add-instance.md).

Then see [Entities](usage/entities.md) for what shows up, and [Automations](usage/automations.md) for what you can do with it.

## Requirements

| | |
|---|---|
| Home Assistant | 2025.1 or newer. Tested on 2026.2, 2026.8 and 2026.10. |
| Kitlig | 0.14.0 or newer, with its server reachable on your network. |
| Newer Kitlig builds | Project spend and automatic discovery need a build newer than 0.14.0. Everything else works without them. |
