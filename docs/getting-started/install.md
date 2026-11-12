# Install

You can install with HACS or by copying a folder. Either way, Home Assistant needs a restart afterwards.

## With HACS

1. Open **HACS** in Home Assistant.
2. Open the **⋮** menu and choose **Custom repositories**.
3. Paste `https://github.com/UAI-Software-Inc/Kitlig-Home-Assistant-Integration`, choose **Integration** as the type, and select **Add**.
4. Find **Kitlig** in HACS and select **Download**.
5. Restart Home Assistant.

HACS tells you when a new version is out.

## By hand

1. Download this repository.
2. Copy the folder `custom_components/kitlig` into the `custom_components` folder of your Home Assistant configuration. Create `custom_components` if it is not there.
3. Restart Home Assistant.

The result should look like this:

```text
config/
  custom_components/
    kitlig/
      __init__.py
      manifest.json
      ...
```

To update, replace the `kitlig` folder with the new one and restart.

## Check that it loaded

After the restart, go to **Settings ▸ Devices & services ▸ Add integration** and search for **Kitlig**. If it is in the list, the install worked.

Home Assistant writes a warning to its log that a custom integration was found. That is normal for anything installed this way.

Next: [Prepare Kitlig](prepare-kitlig.md).
