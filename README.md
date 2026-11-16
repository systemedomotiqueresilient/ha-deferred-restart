# Deferred Restart

<img src="https://raw.githubusercontent.com/systemedomotiqueresilient/ha-deferred-restart/main/custom_components/deferred_restart/brand/icon.png" alt="Deferred Restart" width="128">

[![Validate](https://github.com/systemedomotiqueresilient/ha-deferred-restart/actions/workflows/validate.yml/badge.svg)](https://github.com/systemedomotiqueresilient/ha-deferred-restart/actions/workflows/validate.yml)

🇬🇧 English · 🇫🇷 [Français](README.fr.md)

A Home Assistant integration that **defers** a voluntary restart when it would prevent a
scheduled or predictable automation from running. The restart is not refused: it is queued
and runs automatically as soon as the window is clear.

## Installation

### HACS (custom repository)

1. HACS → ⋮ menu → **Custom repositories**
2. Add `https://github.com/systemedomotiqueresilient/ha-deferred-restart`, category **Integration**
3. Install **Deferred Restart**, then restart Home Assistant
4. **Settings → Devices & services → Add integration → Deferred Restart**

### Manual

Copy `custom_components/deferred_restart/` into your `config/custom_components/` folder,
restart, then add the integration as above.

## How it works

For every trigger due at time `T`, the range `[T − 15 min, T + 5 min]` is protected
(both durations are configurable). If the automation is still running at `T + 5`, protection
is extended until it finishes.

Supported triggers (enabled automations only):

| Trigger | Details |
|---|---|
| `time` | fixed time, `input_datetime` (date, time or both), timestamp `sensor`, `offset` |
| `time_pattern` | ignored if it fires more often than the minimum interval (60 min by default) |
| `sun` | sunrise / sunset with offset |
| `calendar` | event start / end with offset (read cached for 5 min) |

State, motion, presence, MQTT, event, template… triggers are unpredictable, so they are
deliberately ignored.

## Behaviour

- `homeassistant.restart` is intercepted (UI, automation, script).
- Window clear: the restart happens immediately.
- Protected window: the request is queued and a persistent notification is created.
  From the UI or a HACS "Restart required" repair, an error message explains why.
  From an automation or a script, nothing fails (silent deferral).
- The window is re-evaluated every 30 s. As soon as it is clear, the restart runs.
- A maximum deferral time (60 min by default, 0 = unlimited) forces the restart if needed.

## Entities

- `binary_sensor.deferred_restart_safe_now`: `on` if restarting now would disturb nothing (`reasons` attribute)
- `binary_sensor.deferred_restart_pending`: a restart is queued (`pending_since`, `deadline`)
- `sensor.deferred_restart_next_scheduled_trigger`: next predictable trigger within 24 h
- `switch.deferred_restart_protection`: off = protection paused (development mode).
  It turns itself back on after the pause duration (120 min by default, `resume_at` attribute).
  The pause survives restarts, so you can loop edit → restart → test without re-arming it.
  Turning the switch off also releases a restart that is already queued.

## Actions

- `deferred_restart.force_restart`: runs the queued restart, or restarts right away without checks
- `deferred_restart.cancel_pending`: drops the deferred restart

## Main use case: HACS / Marketplace integrations

After installing or updating an integration, HACS offers a "Restart required" repair that calls
`homeassistant.restart`: it is intercepted just like Settings → System → Restart. HACS does not
pass on the user who triggered the call, so Deferred Restart recognises this case through the
still-open `restart_required` repair and shows the message.

## Spook compatibility

Spook also replaces `homeassistant.restart` to add a `force` option. Both work together whatever
the loading order: `force: true` is never deferred, and reloading Deferred Restart (after an
options change) does not overwrite Spook's service.

## How it differs from Restart Guard (igraph100)

[Restart Guard](https://github.com/igraph100/ha-restart-guard) **warns** you in the restart
dialog and asks for confirmation; you decide. Deferred Restart **defers** the restart and runs it
automatically once the window is clear. The two use different domains.

## Known limitations

- Restarts started by the Supervisor (`ha core restart`, HAOS/Supervisor updates, watchdog) do not
  go through Home Assistant Core, so they cannot be deferred.
- `update.install` on the Core update entity is not intercepted.
- The integration replaces the `homeassistant.restart` service handler, which relies on an internal
  API. The original handler (including its admin check) is restored when the integration unloads.
- A script started with `script.turn_on` from a scheduled automation is only taken into account
  with the "block for any running automation/script" option.
- Automation conditions are not evaluated: protection is deliberately conservative.

## License

[MIT](LICENSE)
