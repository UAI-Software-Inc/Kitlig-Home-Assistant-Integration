# Add an instance

Each Kitlig you add becomes one device in Home Assistant.

## Add it by address

1. Go to **Settings ▸ Devices & services**.
2. Select **Add integration** and search for **Kitlig**.
3. Fill in the form:

    | Field | What to enter |
    |---|---|
    | Host | The name or IP address of the computer running Kitlig. |
    | Port | `8420`, unless you changed it in Kitlig. |
    | Password | The MCP token or the Kitlig Web password. See [Prepare Kitlig](prepare-kitlig.md#the-password). |

4. Select **Submit**.

The device is named after what Kitlig calls itself, which is the computer's name unless you set another.

## Let Home Assistant find it

Kitlig builds newer than 0.14.0 announce themselves on the network. Home Assistant then lists them under **Discovered** on the Devices & services page. Select **Add**, enter the password, and you are done.

Discovery only works when Home Assistant and Kitlig are on the same network segment. Across routers or VLANs, add the instance by address.

## Add more

Repeat the steps for every Kitlig. See [Several instances](../usage/several-instances.md) for how they are kept apart.

## If sign-in fails

| Message | What to do |
|---|---|
| Could not reach Kitlig at that address | Check the host and port, that Kitlig is running, and that **Listen on network** is on. |
| Kitlig did not accept that password | Copy the MCP token again from Kitlig's Settings ▸ MCP Server page. |
| Phone companion is off | Turn on **Phone companion** in Kitlig's Settings ▸ MCP Server. |
| Maximum of 10 signed-in devices | Remove a device in Kitlig's Settings ▸ MCP Server ▸ Devices, then try again. |
| Too many sign-in attempts | Wait a minute. Kitlig allows five tries per minute. |

## Later changes

**Kitlig moved to another address.** Open the instance on the Devices & services page, open its **⋮** menu and choose **Reconfigure**. Enter the new address and the password. Your entities and their history stay.

**Home Assistant asks you to sign in again.** This happens when Home Assistant was removed from Kitlig's device list, or the list was reset. Enter the password again and everything carries on.

**Remove an instance.** Choose **Delete** in the instance's **⋮** menu. Home Assistant signs out of Kitlig as it goes, which frees the device slot.
