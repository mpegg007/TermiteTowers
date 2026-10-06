<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: hams/docs/hal-context.md:172 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: c62d0ef3bce968e7b3cf896e0045423791418380 % -->
<!-- %ccm_git_commit_id: 7ca87689c10da1e8ecebbe33bc2b42897f22b48c % -->
<!-- %ccm_git_commit_count: 172 % -->
<!-- %ccm_git_commit_date: 2026-10-05 20:46:08 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: house layout + routines docs % -->
<!-- %ccm_git_modify_date: 2026-10-05 20:46:09 % -->
<!-- %ccm_git_file_last_modified: 2026-10-05 20:20:28 % -->
<!-- %ccm_git_file_name: hal-context.md % -->
<!-- %ccm_git_path: hams/docs/hal-context.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: utf-8 % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 18305 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
 <!-- %git_commit_history: 2026-10-01 Matthew Pegg  hal.1001.bosman  --> 
<!-- %git_commit_history: 2026-09-25 mpegg  cleanup  % -->
<!-- %git_commit_history: 2026-09-25 mpegg  cleanup  % -->
# HAL Context — Home Assistant instance snapshot

> **What this is:** a cache of the *static and slowly-changing* facts about the
> "HAL" Home Assistant instance, so an agent doesn't re-derive the house model,
> naming conventions, and integration stack from scratch every session.
>
> **What this is NOT:** an authority for anything that gates a change. Entity
> *states*, availability, battery levels, versions, and add-on run-states must
> **always be queried live** (see "Do not trust here" at the bottom). A context
> doc shortens discovery; it never authorizes an action.

- **Last refreshed:** 2026-10-01 (automation inventory + bedroom-door latch chain; remaining sections as-of 2026-09-15)
- **Maintained by:** regenerated from the `hal-mcp` MCP tools (see "How to refresh")
- **Related docs (one leads to another):**
  - [SKILL.md](SKILL.md) — HA development skill (triggers on "HAL")
  - [sensors.md](sensors.md) · [dashboards.md](dashboards.md) · [integrations.md](integrations.md) — generic HA references
  - [hams/README.md](../README.md) — directory index
  - [ESPHome](../esphome/README.md) · [ESP32 naming](../esphome/ESP32-Naming-Standard.md)
  - [HAL bridge runbook](../../wiki/runbook-ha-hal-bridge.md) · [ha-handler runbook](../../wiki/runbook-ha-handler.md) · [Device naming](../../wiki/Device-Naming-Standard.md)

---

## 1. How to reach HAL

- **MCP namespace:** `hal-mcp__*` (Home Assistant OS/Supervised — Supervisor-backed add-ons).
- **Home Assistant:** `http://homeassistant.local:8123`
- **LLM → HA bridge:** `llm-ha-handler-dev1` (systemd) → Flask `/hal` endpoint on port `5000`; depends on LM Studio OpenAI-compatible API at `localhost:1234`. See `wiki/runbook-ha-hal-bridge.md` and `wiki/runbook-ha-handler.md`.
- **Source of truth for device naming:** `hams/esphome/ESP32-Naming-Standard.md`, `wiki/Device-Naming-Standard.md`.

---

## Data sources (MCP → databases)

Three read-only MCP servers are available; two are Postgres.

| MCP | Database | Key schemas/tables | Join keys with HAL |
|---|---|---|---|
| `hal-mcp__*` | — (Home Assistant) | entities, devices, automations, add-ons | `identifiers`, `mac`, `ieee_address`, `mqtt_topic` |
| `pg-query-ttdb__*` | main (network/home) | `dhcp_history` (lease_events, device_summary), `kea`, `watchyourlan`, `water_meter`, `powerdns`, `nextcloud`, `snipeit` | `mac_address`, `ip_address`, `hostname` |
| `pg-query-ttphoto__*` | photo library | `images`, `image_tags`, `tag_history`, `stacks` | (none with HAL) |

Join HAL ↔ `ttdb` on **MAC / IP / hostname** (e.g. `ha_get_device` `identifiers` ↔ `dhcp_history.device_summary.mac_address` / `watchyourlan.now`).

---

## 2. House topology (STATIC)

5 floors, 18 areas.

| Floor (level) | Areas | Climate sensor (temp / humidity) |
|---|---|---|
| **Basement** (-1) | Basement | `sensor.esp32_boiler_boiler_room_*` (also `mwave_basement_*` present) |
| **Utility** (—) | Utility | none |
| **Ground** (1) | Entry, Kitchen, Living Room, Hallway, Green Room (`hobby_room`), Laundry, Bathroom, Backroom (`workout`), Sauna, Catio | Entry `mwave_entry_*` · Kitchen `mwave_kitchen_*` · Living Room `mwave_living_tv_*` · Bathroom `mwave_1stbath_*` |
| **Second** (2) | Bedroom, Library, Master Bath, Office, 2nd Hallway | Bedroom `esp32_node06_*` · Master Bath `mwave_masterbath_sink_*` · Office `mwave_office_*` |
| **Attic** (3) | Cattic | none |

Physical notes:
- **Basement is L-shaped ~18×40 ft with a 6×12 ft corner missing, heavily obstructed.** The boiler lives down here (`esp32_boiler`). One PIR/one mmWave is not enough; planned for 3 mmWave zones + PIR at entry.
- Front door is a **Ring** (motion/ding events + camera) with **no open/closed contact sensor**.
- Cat spaces: **Catio** (outdoor two-level cat deck — lower off the Laundry, upper off the Bedroom) and **Cattic** (the walkable attic; detail in [house-layout.md](house-layout.md) §2.8).

---

## 3. Sensor families & naming conventions (STATIC)

| Prefix / pattern | Hardware | Integration | What it exposes |
|---|---|---|---|
| `mwave_<room>_*` | HOBEIAN "Millimeter wave motion detection" | Zigbee2MQTT (MQTT) | presence, illuminance, temperature, humidity, battery, `fading_time`, `motion_detection_sensitivity` |
| `pir_<room>_*` | Tuya "Motion sensor" (PIR) | Zigbee2MQTT (MQTT) | occupancy, battery, voltage, tamper |
| `esp32_nodeNN_*` | ESP32 (ESPHome) | ESPHome | temp/humidity/etc. per node config in `hams/esphome/` |
| `basement_water_leak_*` | leak sensor | (Z2M) | moisture, battery, tamper |
| `dishwasher1_*`, `refrigerator_*` | smart appliances | vendor | door, chime sound, notifications |
| `vibration_laundry_*` | laundry vibration | (Z2M) | vibration |
| Echo Dots | Amazon Alexa | Alexa | `*_echo_dot_*` connectivity / voice events / media_player |
| `l40_*` | Litter-Robot 4 (L40) | Litter-Robot | cycle, backup map, notifications |
| `55_sharp_roku_tv_*` | Roku TV | Roku | playback/connectivity |
| `nextcloud_termitetowers_ca_*` | Nextcloud | Nextcloud | system status |

**mmWave presence sensors (8, all HOBEIAN via Z2M):**
`1stbath`, `basement`, `bedroom`, `entry`, `kitchen`, `living_tv`, `masterbath_sink`, `office`.
Each exposes `binary_sensor.mwave_<room>_presence` (the occupancy signal).

**PIR motion sensors (2, all Tuya via Z2M):** `basement`, `dabrig`.

**Door/window contact sensors: 3 deployed, rollout in progress** (SONOFF contacts via Z2M) — `binary_sensor.bedroom_door`, `binary_sensor.catio_door` (Laundry ↔ Catio lower deck) and `binary_sensor.sauna_door`. The front door is still Ring-only; the 4th contact is spare; deck/cat-door/window openings are pending. Full plan, naming contract and live status: [zigbee-door-sensor-rollout.md](zigbee-door-sensor-rollout.md).

---

## 4. Integration & add-on stack (SLOW — verify before acting)

**Add-ons (Supervisor):**

| Add-on | Slug | State (as-of) |
|---|---|---|
| Matter Server | `core_matter_server` | started |
| Node-RED | `a0d7b954_nodered` | **stopped** (update avail; `protected:true`; boot manual) |
| File editor | `core_configurator` | started |
| Music Assistant | `d5369777_music_assistant` | stopped |
| Zigbee2MQTT | `45df7312_zigbee2mqtt` | started |
| Mosquitto broker | `core_mosquitto` | started |

**Transport:** Zigbee devices → Zigbee2MQTT → Mosquitto MQTT → HA. ESP32 nodes → ESPHome direct.

**No Node-RED "Companion" (`nodered`) integration** exists — therefore no `nodered.*` services/entities anywhere.

---

## 5. Automation inventory (SLOW — partial detail, regenerate for full)

**52** automations exist (`42 on` / `9 off` / `1 unavailable` as of 2026-10-01; query returned `partial:false`).
Fully-inspected ones are described below; the rest are name-only.

> A name-only list of **40** was recorded here through 2026-09-15. It silently omitted **12** automations —
> the eight live members of the bedroom door-latch chain, plus `catio_door_indicator`,
> `catio_door_open_when_away`, `sauna_door_cat_water_guard`, and `library_pole_bedtime_fade`. Treat any
> inventory in this file older than 2026-10-01 as under-counting; always re-query the live count.

Verified in detail:
- `lights_on_basement` — `motion_light` blueprint on `binary_sensor.pir_basement_occupancy`, target area `basement`, `no_motion_wait: 600` (this is the "goes dark while I'm still there" problem — PIR, not presence).
- `sleep_temp` / `sleep_cool_off` — time-pattern triggers, condition on `sensor.esp32_node06_esp32_node06_temperature`, set a climate to cool/heat.
- `matt_falls_asleep` — `input_button.matt_falls_asleep` → `script.matt_bedtime_winddown` (headboard button can cancel).
- `bedroom_dark` — on a bedroom light turning off, 23:30–05:00, turns off a remote + switch + lights.
- `office_light_status`, `turn_off_office_lights`, `turn_on_cattic_lights` — conversation-intent automations.
- **Bedroom door-latch chain (8 live-adjacent + 3 disabled).** All of them key off `binary_sensor.bedroom_door`.
  The two latch flags are `input_boolean.bedroom_door_verified_shut` and `input_boolean.bedroom_night_settled`.
  - `bedroom_door_verified_shut` — **the armer. No conditions at all.** Trigger: door `to: off` **for 2 minutes**;
    single action `input_boolean.turn_on` on `bedroom_door_verified_shut`. (config hash `3cb50db6fb384f31`)
  - `bedroom_door_closed_settle_in` — **the night armer.** Trigger: door `to: off` for 5 s; gated by time
    **21:00–05:30**; action 4 is `input_boolean.turn_on` on `bedroom_night_settled`. All 5 retained traces are
    `failed_conditions`, i.e. it has never yet actually set the flag. Re-touched today, reload 08:56:50.554.
  - `bedroom_door_opened_morning` (alias `bedroom-door-opened-morning`) and `bedroom_door_opened_night` — **the
    consumers.** Both gate on `verified_shut = on` **AND** `night_settled = on` **AND** a time window
    (`opened_morning`: 05:30–12:00).
  - `bedroom_night_settled_reset` — clears `night_settled`.
  - Disabled trio (earlier attempts, all `off` since 2026-09-24T17:14): `bedroom_door_closed_arms_sleep`,
    `bedroom_night_exit_nightlight`, `bedroom_wake_release`.
- **The latch is CONSUMED, not broken — and the guard is currently inert.** `bedroom_door_opened_morning`'s
  stored config was reloaded/edited at **2026-10-01 08:52:35.866** (runtime config hash `e84c51ea62d05e7b`;
  **3** conditions — `verified_shut=on`, `night_settled=on`, time 05:30–12:00). Its `last_triggered` is
  **08:38:05** — *before* that reload — and its 5-slot trace set holds **no post-reload door-triggered run**:
  one `failed_conditions` manual negative test (`b3631fbad…`, where `condition/0`=true on the time gate and
  `condition/1`=false on `night_settled`, with no trigger platform) plus four `finished` runs from the
  **pre-reload 2-condition** config (`fad9d2cd…` 08:38:05, `dc83b7c0…` 08:07:16, `666df97a…` 06:19:54,
  `e4fe4f25…` 05:31:40 — the last carries **3** condition records and is the pre-reload proof). So under the
  current config the `verified_shut` condition has **zero executions** — stored, loaded, never fired. Under the
  pre-reload config every door event *did* execute and cleared **both** flags; the latch is then re-armed by
  the door's **own 2-minute debounce** (`bedroom_door_verified_shut` turning `verified_shut` back on).
  `night_settled`'s `last_changed` of 05:31:40.359 sits on the exact second of a door event that cleared both
  flags — consistent with consume-then-re-arm, not a faulty sensor. Caveat: trace retention is only **5 slots**
  per automation (`has_more:false`), so the absence of a post-reload run is on its own weak evidence; it is the
  un-moved `last_triggered` that makes the case.

Full entity list (**52**, complete as of 2026-10-01):
`badtime_tv`, `bedroom_dark`, `bedroom_door_closed_arms_sleep`, `bedroom_door_closed_settle_in`, `bedroom_door_opened_morning`, `bedroom_door_opened_night`, `bedroom_door_verified_shut`, `bedroom_night_exit_nightlight`, `bedroom_night_settled_reset`, `bedroom_sleep_now`, `bedroom_wake_release`, `boiler_off`, `catio_at_dawn`, `catio_at_dusk`, `catio_door_indicator`, `catio_door_open_when_away`, `cattic_off`, `door_layer_alert`, `door_layer_cross_check`, `door_unlocked_too_long`, `glucose_over_7`, `headboard_kill_all`, `kitchen_motion`, `l40_clean_cat_box_on_litter_robot_cycle`, `library_pole_bedtime_fade`, `lights_on_basement`, `llm_hooktest_1` (YAML-defined, see gotchas), `matt_bedtime_armed_reset`, `matt_bedtime_prep`, `matt_falls_asleep`, `matt_leaves_bathroom`, `matt_lights_bathroom`, `matt_morning_macro_auto`, `matt_morning_macro_reset`, `matt_office_daytime_after_shower`, `matt_shower_detected`, `matt_shower_done_reset`, `morning_boiler`, `office_light_status`, `omp_bedtime`, `sauna_door_cat_water_guard`, `sleep_cool_off`, `sleep_temp`, `sleep_trigger`, `steve_enters_home`, `steve_morning_greeting`, `turn_off_office_lights`, `turn_on_cattic_lights`, `turn_on_office_lights`, `tv_off_lights_out`, `water_meter`, `witness_watchdog_alert`.

The **12** names added on 2026-10-01 (absent from the earlier 40-name list) are the eight door-chain members
detailed above — `bedroom_door_closed_arms_sleep`, `bedroom_door_closed_settle_in`,
`bedroom_door_opened_morning`, `bedroom_door_opened_night`, `bedroom_door_verified_shut`,
`bedroom_night_exit_nightlight`, `bedroom_night_settled_reset`, `bedroom_wake_release` — plus
`catio_door_indicator`, `catio_door_open_when_away`, `sauna_door_cat_water_guard`, and
`library_pole_bedtime_fade`. Those last four are still name-only.

---

## 6. People & sleep model (STATIC-ish)

- Two people appear in automations: **matt** and **steve**. HA account is `mpegg` (Matthew Pegg).
- Existing bedtime machinery: `matt_falls_asleep` (headboard button) → `script.matt_bedtime_winddown`; `bedroom_dark` overnight shutdown; scene `mpegg_bedtime_tv`.
- **Planned sleep derivation:** bedroom door-closed **AND** `binary_sensor.mwave_bedroom_presence` **AND** time window → "someone sleeping" (complements, not replaces, the manual button).

---

## 7. Known gotchas (STATIC)

- **One YAML-defined automation** — `automation.llm_hooktest_1` — is **not** readable via the REST config endpoint (returns 404). Its body lives in `automations.yaml`, not HA storage. Any "scan all automations" must account for this blind spot.
- **`binary_sensor.bedroom_door` — magnet gap (fixed 2026-09-24; the physical mounting fix is permanent — a sensor-mount fix, not a software gate).** The contact only detected the magnet as it **swept past**, so a shut door read `on` and an `off → on` ("door opened") trigger fired on *closing* — switching off the bedroom night lights at 22:17:46 on 2026-09-23. After moving the magnet the door held `off` continuously for 2 min 51 s. **Guard claim corrected 2026-10-01:** `input_boolean.bedroom_door_verified_shut` is a **latch, not an enforced gate**. The `bedroom-door-verified-shut` automation *sets* it after the door reads `off` for 2 minutes; the door-open automations merely *test* it (`verified_shut = on` AND `night_settled = on` AND a time window). The earlier wording here — that it "requires the door to read `off` for 2 minutes before any 'door opened' automation will run" — described the *intent* and was never verified against runtime behaviour. Under the config loaded at 2026-10-01 08:52:35.866 that latch condition has **zero executions** (no post-reload door-triggered trace; `last_triggered` 08:38:05 predates the reload), and the latch is **consumed by the very door events it guards** then re-armed by the door's own 2-minute debounce. Full mechanic + trace evidence in §5. A plain duration debounce on `on` does **not** work here — after a glitch the state stays `on`. Bedroom logic (`bedroom-door-…` are the automations' **aliases**; the live `entity_id`s use underscores): `automation.bedroom_door_verified_shut`, `automation.bedroom_door_opened_night`, `automation.bedroom_door_opened_morning`, `automation.bedroom_door_closed_settle_in`, `automation.bedroom_night_settled_reset`; the three earlier attempts are disabled (`automation.bedroom_door_closed_arms_sleep`, `automation.bedroom_night_exit_nightlight`, `automation.bedroom_wake_release`, all `off` since 2026-09-24 17:14). Details: [zigbee-door-sensor-rollout.md](zigbee-door-sensor-rollout.md) § Incident log.
- **`scene.daytime` whitens the 2nd-floor lights.** It sets `light.bulb_secondfloor_stair_hallway` (5000 K @199) and `light.bulb_masterbath_ceiling_light` (5000 K @184), applied by `automation.matt_office_daytime_after_shower` — so a night-time red night path can jump to bright white when that chain fires.
- **`mwave-basement` is battery-powered** — battery mmWave can be slow to trigger/clear; prefer mains for "hold the lights" duty.
- **mmWave false-positives** from heat/fans: keep basement mmWave pointed away from the boiler and vents, mount high and angled down.
- **Node-RED** add-on is stopped and being considered for removal; flows are deleted on uninstall — back up first. No HA-side references to it.

---

## 8. DO NOT TRUST HERE — always query live

Never read these from this file; always query via MCP at decision time:
- Any **entity state** (on/off, occupancy, temperature, humidity, illuminance, battery, voltage).
- **Availability / connectivity** of any entity, device, or add-on.
- **Add-on / integration versions and run-states** (started/stopped, update-available).
- The current **entity registry** (exact IDs change as sensors are added/renamed).

---

## 9. How to refresh this file

Regenerate from the MCP in one pass:

1. `hal-mcp__ha_list_floors_areas` → topology table.
2. `hal-mcp__ha_search` with `domain_filter=binary_sensor` / `sensor` → entity inventory.
3. `hal-mcp__ha_get_app` → add-on stack + states.
4. `hal-mcp__ha_get_integration` / `ha_list_services` → integration stack.
5. `hal-mcp__ha_get_device` per sensor family → hardware → integration mapping.
6. `hal-mcp__ha_search` with `domain_filter=automation` + `ha_config_get_automation` → automation inventory.

Bump "Last refreshed" and the as-of notes when done.

