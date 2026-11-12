# Troubleshooting

## Kitlig is not in the Add integration list

- Restart Home Assistant after installing. It only looks for new integrations when it starts.
- Check that the folder is `config/custom_components/kitlig` and that `manifest.json` is directly inside it.

## Sign-in fails

See the table in [Add an instance](getting-started/add-instance.md#if-sign-in-fails). To find out which side the problem is on, open `http://<kitlig-computer>:8420/api/me` in a browser, as described in [Prepare Kitlig](getting-started/prepare-kitlig.md#check-that-it-is-reachable).

If that page loads from your own computer but Home Assistant cannot connect, the Home Assistant machine cannot reach the Kitlig machine. A firewall on the Kitlig computer is the usual cause.

## Everything is unavailable

Home Assistant cannot reach Kitlig. The **Connected** entity is off.

- Is Kitlig running? Its server stops when Kitlig closes.
- Did the computer's address change? Use **Reconfigure** to enter the new one.
- Did the port or the **Listen on network** setting change?

The entities come back by themselves when Kitlig is reachable again.

## Values read 0 or unknown

| What you see | Why |
|---|---|
| Counts are 0, **Open project** is unknown | No project is open on that Kitlig. |
| **Current job** and its progress are unknown | No job is running. |
| **Current job progress** is unknown while a job runs | That job does not report a percent. |
| **Project spend** is unknown | Your Kitlig is 0.14.0 or older, or no project is open. |
| **Job** event is unknown | No job has finished, failed, been cancelled or asked a question since the instance was added. |

## Home Assistant asks me to sign in again

Kitlig no longer accepts Home Assistant's sign-in. Someone removed "Home Assistant" from Kitlig's device list, or the list was reset. Enter the password again.

Kitlig also forgets a device it has not heard from in 30 days. That cannot happen while Home Assistant is running, but it can if Home Assistant was off for a month.

## The same Kitlig shows up as discovered again

This happens once if you added the instance by address on Kitlig 0.14.0 and later updated Kitlig to a build that announces itself. Home Assistant knows the first one by its address and the new one by its ID.

Either select **Ignore** on the discovered one, or delete the old instance and add the discovered one. Deleting and re-adding gives the entities new history.

## A site or game does not open

- **The new tab cannot connect.** The link points at Kitlig, so your browser has to be able to reach the Kitlig computer. Away from home that will not work unless Kitlig is reachable from there. See **Address browsers should use** in the [options](reference/options.md).
- **"This preview link has expired."** Links last 12 hours. Select Open or Play again for a fresh one.
- **Nothing happens when I select Open.** Your browser blocked the new tab. Allow pop-ups for your Home Assistant address.

## The Kitlig card is missing or says "Custom element doesn't exist"

Refresh the browser, or clear the Home Assistant app's frontend cache. The card is loaded when the integration starts, so a dashboard that was already open does not have it yet.

## Media does not play

- Check that the file plays in Kitlig. Home Assistant passes the file along as it is and does not convert it.
- Some formats, such as ProRes or EXR, do not play in browsers at all.
- On a slow link, large exports take a while to start.

## Job control does nothing

A Kitlig started with `KITLIG_WEB_READ_ONLY=1` refuses to cancel or retry jobs. The buttons are left out for such an instance, and the actions return an error.

## The logo does not show

Home Assistant 2026.3 and newer show the integration's own logo. Older versions show a placeholder. After installing or updating, restart Home Assistant and refresh the browser.

## Getting more detail

Turn on debug logging for one instance from its page: **⋮ ▸ Enable debug logging**. Reproduce the problem, then turn it off, and Home Assistant downloads the log.

**Download diagnostics** on the same menu gives a snapshot of what the integration currently knows. The sign-in token is removed from it. Please attach both when you [report a problem](https://github.com/UAI-Software-Inc/Kitlig-Home-Assistant-Integration/issues).
