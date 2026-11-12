# Several instances

You can add every Kitlig you run: a workstation, a render box, a Docker install on a server. Each is added the same way, as described in [Add an instance](../getting-started/add-instance.md).

## How they are kept apart

- **One device each.** Every instance is its own device, named after the Kitlig, with its own full set of entities.
- **Entity IDs carry the name.** A Kitlig called "Studio" gets `sensor.studio_jobs_running`. One called "Render Box" gets `sensor.render_box_jobs_running`.
- **A stable identity.** Newer Kitlig builds give each install an ID that does not change. Home Assistant uses it to recognise an instance, so adding the same Kitlig twice is refused, and an instance whose address changed is updated instead of duplicated. Kitlig 0.14.0 and older are recognised by their address instead.

## Where instances show up together

| Place | How instances appear |
|---|---|
| Media browser | A folder per instance, labelled with its open project. |
| Kitlig card | A section per instance. Set **Instance** on a card to show one only. |
| `kitlig_job` event | Every event says which instance it came from. See [Events](../reference/events.md). |

## Actions need to know which one

With one instance, the actions work without saying which Kitlig you mean. With two or more, set the **Instance** field (`config_entry_id`). Leaving it out gives an error asking you to say which one.

Inside an automation triggered by a `kitlig_job` event, the event carries the right value:

```yaml
- action: kitlig.cancel_job
  data:
    config_entry_id: "{{ trigger.event.data.config_entry_id }}"
    job_id: "{{ trigger.event.data.job_id }}"
```

## Adding them up

A template sensor gives you one number for all instances:

```yaml
template:
  - sensor:
      - name: Kitlig jobs running everywhere
        state: >-
          {{ states('sensor.studio_jobs_running') | int(0)
             + states('sensor.render_box_jobs_running') | int(0) }}
```

## Renaming

Rename the device in Home Assistant to change how an instance is shown. Home Assistant offers to rename its entities to match. To change what Kitlig calls itself, set `KITLIG_WEB_SERVER_NAME` on a Docker or headless install. The Home Assistant name does not follow that change by itself.
