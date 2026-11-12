# Entities

Every instance gets the same set of entities. Their IDs start with the instance's name, so a Kitlig called "Studio" has `sensor.studio_jobs_running`, `binary_sensor.studio_working` and so on.

All of them describe the project that is open on that Kitlig. With no project open, counts read `0` and the rest read `unknown`.

## Sensors

| Entity | State | Attributes |
|---|---|---|
| **Jobs running** | Number of jobs running now. | `jobs`: a list with each job's `job_id`, `label`, `status`, `progress`, `phase`, `message` and `started`. |
| **Jobs queued** | Number of jobs waiting to start. | `jobs`: the same list, for queued jobs. |
| **Current job** | Name of the newest running job. | `job_id`, `status`, `progress`, `phase`, `message`, `started`. |
| **Current job progress** | Percent, when the job reports one. | |
| **Open project** | Name of the open project. | `project_id` |
| **Project spend** | What the project has cost so far, in USD. | `today`, `this_week`, `this_month`, `this_year`, `priced_runs`, `unpriced_runs`, `runs_priced_at_a_default_size`, `project` |
| **Open review comments** | Unresolved review notes across all sequences. | `sequences`: each with `name`, `open_comments`, `latest_export`, `matches_timeline`, `favorites`, `rating` (the average) and `rating_count`. |
| **Sites** | Number of websites in the project. | `items`: each with `site_id`, `name`, `updated`, `pages`. |
| **Games** | Number of games in the project. | `items`: each with `site_id`, `name`, `updated`, `pages` (the scenes). |
| **Version** | Kitlig's version. A diagnostic entity. | |

### About Project spend

This is the figure in Kitlig's status bar set to **Project lifetime**. It is an estimate worked out from the prices of the models the project used.

- Failed and cancelled runs are not counted.
- `unpriced_runs` are runs of models that have no price in Kitlig's catalog. They add nothing to the total.
- `runs_priced_at_a_default_size` are runs where Kitlig did not know the length or size and assumed one.

The sensor reads `unknown` on Kitlig 0.14.0 and older, which do not report spend over the network.

## Binary sensors

| Entity | On when | Attributes |
|---|---|---|
| **Connected** | Home Assistant can reach Kitlig. A diagnostic entity. | `live_updates`: whether the live stream is connected. |
| **Working** | At least one job is running. | |
| **Needs answer** | A job has stopped to ask a question. | `jobs`: the waiting jobs. |

When **Connected** is off, the other entities become unavailable until Kitlig is back.

## Image

**Latest media** shows the newest picture or video poster frame in the project. Use it in a picture card to see the latest result at a glance. Its attributes give the file's `asset_id`, `name`, `kind`, `section`, `origin` and `created`.

## Event

**Job** fires when a job finishes, fails, is cancelled or needs an answer. Its state is the time of the last one, and its `event_type` attribute says which kind it was. See [Events](../reference/events.md) for the details it carries.

It reads `unknown` until the first job event after the instance was added.

## Buttons

| Entity | What it does |
|---|---|
| **Cancel running jobs** | Stops every running and queued job on that Kitlig. |
| **Retry last failed job** | Runs the most recently failed job again with the same inputs. |

A read-only Kitlig has no buttons.

## How fresh the values are

Changes arrive live, usually within a second. Job counts and progress, new media, review comments, sites and games each update when Kitlig reports a change.

A regular check also runs every 30 seconds, and a full refresh every 5 minutes, in case a live update was missed. You can change the 30 seconds in the [options](../reference/options.md).
