# Automations

The usual reason to connect Kitlig to Home Assistant is to be told when something happens. This page shows the common cases.

## Three ways to trigger

| Trigger | Best for |
|---|---|
| **Device trigger** | Building automations in the visual editor. Choose your Kitlig device, then "A job finished", "A job failed", "A job was cancelled" or "A job needs an answer". |
| **The `kitlig_job` event** | One automation for every instance, or when you want the job's details in the message. See [Events](../reference/events.md). |
| **Entity states** | Reacting to a condition that lasts, such as "Working" being on. |

## Tell me when a render lands

This one automation covers every Kitlig you have added.

```yaml
automation:
  - alias: Kitlig job finished
    triggers:
      - trigger: event
        event_type: kitlig_job
        event_data:
          type: finished
    actions:
      - action: notify.mobile_app_my_phone
        data:
          title: "{{ trigger.event.data.instance }}"
          message: "{{ trigger.event.data.label }} is done."
```

## Tell me when a job fails, with the reason

```yaml
automation:
  - alias: Kitlig job failed
    triggers:
      - trigger: event
        event_type: kitlig_job
        event_data:
          type: failed
    actions:
      - action: notify.mobile_app_my_phone
        data:
          title: "{{ trigger.event.data.label }} failed"
          message: "{{ trigger.event.data.error or 'No reason given.' }}"
```

## A job is waiting for an answer

Some jobs stop and ask a question. The **Needs answer** binary sensor stays on until someone answers in Kitlig.

```yaml
automation:
  - alias: Kitlig needs an answer
    triggers:
      - trigger: state
        entity_id: binary_sensor.studio_needs_answer
        to: "on"
        for: "00:02:00"
    actions:
      - action: notify.mobile_app_my_phone
        data:
          message: "A Kitlig job on Studio has been waiting for an answer for two minutes."
```

## A light that shows Kitlig is busy

```yaml
automation:
  - alias: Studio light follows Kitlig
    triggers:
      - trigger: state
        entity_id: binary_sensor.studio_working
    actions:
      - action: "light.turn_{{ trigger.to_state.state }}"
        target:
          entity_id: light.studio_sign
```

## Warn me when a project passes a budget

```yaml
automation:
  - alias: Kitlig project over budget
    triggers:
      - trigger: numeric_state
        entity_id: sensor.studio_project_spend
        above: 50
    actions:
      - action: notify.mobile_app_my_phone
        data:
          message: >-
            {{ state_attr('sensor.studio_project_spend', 'project') }} has now cost
            ${{ states('sensor.studio_project_spend') | float | round(2) }}.
```

## Stop everything at night

```yaml
automation:
  - alias: Stop Kitlig jobs at midnight
    triggers:
      - trigger: time
        at: "00:00:00"
    actions:
      - action: button.press
        target:
          entity_id: button.studio_cancel_running_jobs
```

## Run a failed job again, once

The event carries the job's ID, which the [`kitlig.retry_job`](../reference/actions.md#kitligretry_job) action takes.

```yaml
automation:
  - alias: Retry a failed Kitlig job once
    mode: queued
    triggers:
      - trigger: event
        event_type: kitlig_job
        event_data:
          type: failed
    conditions:
      - condition: template
        value_template: "{{ 'rate limit' in (trigger.event.data.error or '') | lower }}"
    actions:
      - delay: "00:01:00"
      - action: kitlig.retry_job
        data:
          config_entry_id: "{{ trigger.event.data.config_entry_id }}"
          job_id: "{{ trigger.event.data.job_id }}"
```

!!! warning "Avoid retry loops"
    A retried job that fails again fires another failed event. Keep a condition like the one above, or a counter, so an automation cannot retry the same job forever.

## Send a link to a game

```yaml
script:
  send_game_link:
    sequence:
      - action: kitlig.get_site_url
        data:
          site_id: "{{ state_attr('sensor.studio_games', 'items')[0].site_id }}"
        response_variable: link
      - action: notify.mobile_app_my_phone
        data:
          message: "Play it here: {{ link.url }}"
```
