# Events

## `kitlig_job`

Fired on Home Assistant's event bus when a job on any instance reaches one of four points.

| `type` | When |
|---|---|
| `finished` | The job completed. |
| `failed` | The job failed. |
| `cancelled` | The job was cancelled. |
| `needs_answer` | The job stopped to ask a question. |

### Event data

| Field | Example | What it is |
|---|---|---|
| `type` | `finished` | One of the four types above. |
| `job_id` | `job_01JABC...` | The job's ID in Kitlig. |
| `label` | `Image to Video` | The job's name as Kitlig shows it. |
| `status` | `complete` | Kitlig's own status: `complete`, `failed`, `cancelled` or `awaiting-input`. |
| `error` | `Rate limit reached` | The reason, for a failed job. Empty otherwise. |
| `outputs` | `["asset_01J..."]` | IDs of the files the job made, for a finished job. |
| `instance` | `Studio` | The name of the Kitlig it came from. |
| `project` | `Launch Film` | The project that was open. |
| `config_entry_id` | `01JXYZ...` | The instance's ID in Home Assistant. Pass it to the [actions](actions.md). |
| `device_id` | `a1b2c3...` | The instance's device in Home Assistant. |

### Example trigger

```yaml
triggers:
  - trigger: event
    event_type: kitlig_job
    event_data:
      type: failed
      instance: Studio
```

Leave out `instance` to react to every Kitlig, and leave out `type` to react to all four.

## What does not fire an event

- Jobs that had already finished when the instance was added, or when Home Assistant started.
- Progress changes. Use the **Current job progress** sensor for those.
- A job starting. Use the **Working** binary sensor or the **Jobs running** sensor.

## The Job event entity

Each instance also has an event entity, `event.<name>_job`. It records the same four types for that one instance and keeps the last event's details as attributes. It is the easiest way to see recent job events in the device's activity log.

## Device triggers

In the automation editor, choose **Device** as the trigger and pick a Kitlig. Four triggers are offered:

- A job finished
- A job failed
- A job was cancelled
- A job needs an answer

They are the `kitlig_job` event filtered to that device.
