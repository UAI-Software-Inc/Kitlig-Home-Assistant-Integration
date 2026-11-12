# Sites and games card

The Kitlig card lists the websites and games of the open project and opens them in a new browser tab. It comes with the integration, so there is nothing extra to install.

## Add the card

1. Open a dashboard and choose **Edit dashboard**.
2. Select **Add card** and search for **Kitlig**.
3. Set the options and save.

If the card is not in the list, refresh the browser once. Home Assistant loads the card when the integration starts.

## Options

| Option | YAML key | What it does |
|---|---|---|
| Title | `title` | A heading above the card. Optional. |
| Instance | `entry_id` | Show one Kitlig only. Leave empty to show all of them. |
| Show | `show` | `both` (the default), `sites` or `games`. |
| Show running jobs | `show_jobs` | Adds a line per instance with the job count, the current job and a progress bar. On by default. |

In YAML:

```yaml
type: custom:kitlig-card
title: Sites and games
show: both
show_jobs: true
```

To pick one instance in YAML, set `entry_id` to that instance's ID. The visual editor fills it in for you when you choose an instance.

## Using it

Each site or game is a tile with its name and when it was last changed. Select **Open** on a site or **Play** on a game.

- A site with several pages has a page picker next to the button.
- A game with several scenes has a scene picker. Without a choice, it starts at the first scene.

The card shows a short message instead of tiles when a Kitlig is not reachable, when no project is open, or when the project has no sites or games yet.

## About the links

Kitlig makes a fresh link each time you select Open or Play. A link works for 12 hours, and anyone on your network who has it can open the site, so treat it like a share link.

The link points straight at Kitlig, not at Home Assistant. Your browser has to be able to reach the Kitlig computer. If your browser reaches Kitlig at a different address than Home Assistant does, set **Address browsers should use** in the [options](../reference/options.md).

!!! note "Away from home"
    Media plays through Home Assistant, so it works remotely. Site and game links do not, unless Kitlig itself is reachable from where you are.

## Links in automations

The [`kitlig.get_site_url`](../reference/actions.md#kitligget_site_url) action returns the same kind of link, for example to send one in a notification.
