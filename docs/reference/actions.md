# Actions

Three actions are available under the `kitlig` domain. Each takes an optional **Instance** field, `config_entry_id`. With one Kitlig added you can leave it out. With several it is required.

To find an instance's ID, choose the instance in the action's visual editor and switch to YAML, or take `config_entry_id` from a [`kitlig_job` event](events.md).

## `kitlig.cancel_job`

Stops a running or queued job.

| Field | Required | What it is |
|---|---|---|
| `config_entry_id` | With several instances | Which Kitlig. |
| `job_id` | Yes | The job to stop. |

```yaml
action: kitlig.cancel_job
data:
  job_id: job_01JABCDEFGHJKMNPQRSTVWXYZ0
```

## `kitlig.retry_job`

Runs a failed or cancelled job again with the same inputs and files.

| Field | Required | What it is |
|---|---|---|
| `config_entry_id` | With several instances | Which Kitlig. |
| `job_id` | Yes | The job to run again. |

```yaml
action: kitlig.retry_job
data:
  job_id: job_01JABCDEFGHJKMNPQRSTVWXYZ0
```

## `kitlig.get_site_url`

Returns a link that opens a site or game in a browser. The link works for 12 hours. This action only returns data, so call it with a response variable.

| Field | Required | What it is |
|---|---|---|
| `config_entry_id` | With several instances | Which Kitlig. |
| `site_id` | Yes | The site or game. |
| `page` | No | A page file such as `about.html`, or `index.html?scene=level2.json` for a game scene. Opens the start page when left out. |

```yaml
action: kitlig.get_site_url
data:
  site_id: site_01JABCDEFGHJKMNPQRSTVWXYZ0
response_variable: link
```

The response:

| Field | Example |
|---|---|
| `url` | `http://kitlig-pc:8420/view/.../landing/` |
| `expires_at` | `2026-11-12T22:00:00.000Z` |

## Where the IDs come from

| ID | Where to find it |
|---|---|
| Job ID | The `jobs` attribute of **Jobs running** and **Jobs queued**, the attributes of **Current job**, and the `job_id` of a `kitlig_job` event. |
| Site ID | The `items` attribute of the **Sites** and **Games** sensors. |

## Errors

An action fails with a message when the Kitlig is not connected, when the job or site does not exist, or when the Kitlig is read-only. In an automation, a failed action stops the run unless you set `continue_on_error: true` on that step.
