# Prepare Kitlig

Home Assistant talks to Kitlig over your network. By default Kitlig only listens to its own computer, so three settings need to be on first.

## On a desktop Kitlig

Open **Settings ▸ MCP Server** in Kitlig and turn on:

1. **The server.** This starts Kitlig's built-in server.
2. **Listen on network.** Without it, only programs on the same computer can connect.
3. **Phone companion.** This is the part Home Assistant talks to. It is the same web API the Kitlig phone app uses.

The port is `8420` unless you changed it on that page.

## On a Docker or headless Kitlig

Nothing to do. A headless Kitlig has all three on already.

## The password

Home Assistant signs in once with a password. You can use either of these:

- **The MCP token** shown on the Settings ▸ MCP Server page. It always works.
- **The Kitlig Web password**, if you set one with `KITLIG_WEB_PASSWORD` on a Docker or headless install.

Home Assistant does not keep the password. Kitlig hands back a device token, and that is what gets stored. Home Assistant then shows up as "Home Assistant" in Kitlig's device list, where you can remove it at any time.

!!! note "Device slots"
    Each Kitlig allows 10 signed-in devices. Home Assistant uses one of them. Phones signed in to the Kitlig app use the others.

## Check that it is reachable

From any computer on your network, open this address in a browser, with your Kitlig computer's name or IP address in place of `kitlig-pc`:

```text
http://kitlig-pc:8420/api/me
```

| You see | It means |
|---|---|
| `{"error":"unauthorized", ...}` | Ready. Kitlig is reachable and the phone companion is on. |
| `{"error":"not_found", ...}` mentioning Kitlig Web | The server is on, but **Phone companion** is off. |
| The page does not load | Kitlig is not running, **Listen on network** is off, or a firewall is blocking the port. |

!!! warning "Read-only instances"
    A Kitlig started with `KITLIG_WEB_READ_ONLY=1` refuses job control. Home Assistant still shows everything, but leaves out the two buttons.

Next: [Add an instance](add-instance.md).
