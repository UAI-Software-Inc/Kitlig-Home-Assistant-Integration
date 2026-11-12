# Options

Each instance has its own options. Open the instance on the **Settings ▸ Devices & services** page and select **Configure**.

Saving reloads that instance, which takes a second or two.

## Check every (seconds)

How often Home Assistant asks Kitlig for its state.

| | |
|---|---|
| Default | 30 |
| Range | 10 to 3600 |

Changes normally arrive live, so this check is a safety net. Raise it if you want less traffic to a Kitlig that is often asleep. Lower it only if live updates do not get through on your network. The **Connected** entity's `live_updates` attribute tells you whether they do.

## Address browsers should use

The address your browser should use to open sites and games on this Kitlig, for example `https://kitlig.example.com`.

Leave it empty in the usual case, where your browser reaches Kitlig at the same address Home Assistant does.

Set it when:

- Kitlig sits behind a reverse proxy or has a public name.
- Home Assistant reaches Kitlig by an address your browser cannot use, such as a Docker network name.
- Your Home Assistant is served over HTTPS and you have put Kitlig behind HTTPS as well.

Only the site and game links change. Home Assistant keeps talking to Kitlig at the address you entered when you added it.
