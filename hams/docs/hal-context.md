<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: hams/docs/hal-context.md % -->
<!-- %ccm_git_object_id: hams/docs/hal-context.md@194 % -->
<!-- %ccm_git_commit_date: 2026-10-28 20:22:38 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: misc updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2026-10-10 mpegg docs(hal): correct stale audit facts against live HA -->
 <!-- %git_commit_history: 2026-10-05 mpegg  house layout + routines docs  -->
 <!-- %git_commit_history: 2026-10-01 Matthew Pegg  hal.1001.bosman  -->
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

- **Last refreshed:** 2026-10-18 (`steve_morning_greeting` now triggers on the 45 s debounced `mwave_1stbath_presence_confirmed` and speaks a dry H.U.E.-register line — wording only, since `alexa_devices` delivers the fixed Alexa voice and the 1st Bath has no Cast/ESP32 speaker; 2026-10-15: insulin-trip identity latch: `input_boolean.matt_insulin_trip` + `automation.matt-insulin_trip-arm`, gating `matt-morning-macro-auto` and `matt-shower-detected`; `matt-office-daytime-after-shower` bounded 05:00–12:00; automation inventory **51**, `mister_p_door_indicator` newly listed; 2026-10-14: mmWave anonymity + 30 s keep-time floor + `mwave_1stbath_presence_confirmed` debounce helper; as-of 2026-10-13: contact count 4 + lamp single-writer / catio-indicator precedence; remaining sections as-of 2026-09-15)
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

**Echo speakers are fixed-voice TTS endpoints — the words can change, the timbre cannot.**
`alexa_devices` exposes only `notify.speak` / `notify.announce` on the Echo/Echo Pop
`media_player` entities, so anything spoken on one inherits Alexa's own voice; a custom TTS
voice (e.g. a cloned H.U.E.) requires a speaker with `play_media` / `tts.speak` — Cast or
ESP32. This is why `automation.steve_morning_greeting` was reworded on 2026-10-18 but not
re-voiced: its output device is `media_player.laundry_mpegg_s_echo_pop` in the 1st-floor Bath,
and the house's only Cast speaker, `media_player.bathroom_speaker` (Master Bath), has been
`unavailable` since 2026-10-14.

**mmWave presence sensors (8, all HOBEIAN via Z2M):**
`1stbath`, `basement`, `bedroom`, `entry`, `kitchen`, `living_tv`, `masterbath_sink`, `office`.
Each exposes `binary_sensor.mwave_<room>_presence` (the occupancy signal).

**These sensors are anonymous and quantised by a hardware keep-time** — read this before
building anything identity- or duration-aware on them. A HOBEIAN mmWave reports a single
boolean; Z2M's own exposes for the model are `presence`, `illuminance`, `temperature`,
`humidity`, `fading_time`, `indicator`, `illuminance_interval`,
`motion_detection_sensitivity` (+ calibrations/battery) with **no distance, angle, energy
or velocity** — so a radar **cannot tell you *who* is present**, and no amount of tuning
changes that. `fading_time` (**"motion keep time"**, `30 s` on `mwave-1stbath`, range
0–28800 s) is the **floor on any occupancy blip**: a blip at ~30 s means *one* detection
then nothing (a walk-by), while a genuine stay keeps re-detecting and runs longer.
Measured 2026-10-14 on `mwave-1stbath`: **14 blips, total occupancy ~11 min, longest event
1 min 49 s**, with 6 of the 14 sitting exactly at the 29.7–30.1 s floor. The 1st Bath is
also a **pass-through** room (Green Room barn door, sauna door, and the Backroom with
**no door at all**), so through-traffic cannot be avoided by placement alone.
**Derived debounced signal: `binary_sensor.mwave_1stbath_presence_confirmed`** (template
helper, area `bathroom`, `unique_id 01M4YETE15P5N24EWXQH272JAV`) = the raw sensor gated by
a native **45 s `delay_on`**, so a walk-by never registers (validated live: 45.001 s and
45.004 s turn-on latency). The raw `presence` entity is **unchanged** and stays the signal
for instant-entry logic — the confirmed entity is opt-in per consumer. It has exactly **one
consumer as of 2026-10-18**: `automation.steve_morning_greeting` triggers on the *confirmed*
entity (previously the raw one), accepting the 45 s lag to stop walk-by greetings. Note the write
caveat for `fading_time` / `motion_detection_sensitivity`: this is a battery device that is
"only reachable when active", so those values can only be written **while it is detecting
motion**.

**PIR motion sensors (2, all Tuya via Z2M):** `basement`, `dabrig`.

**Door/window contact sensors: 4 deployed, rollout in progress** (SONOFF contacts via Z2M) — `binary_sensor.bedroom_door`, `binary_sensor.catio_door` (Laundry ↔ Catio lower deck), `binary_sensor.sauna_door` and `binary_sensor.cat_door` (the cat door behind the shelf, paired 2026-10-13; the ex-spare, **polarity unverified**). The front door is still Ring-only, and all four contacts are now spent, so deck/window openings need new hardware. Full plan, naming contract and live status: [zigbee-door-sensor-rollout.md](zigbee-door-sensor-rollout.md).

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

**51** automations exist (`44 on` / `7 off` as of 2026-10-15; query returned `partial:false`).
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

Full entity list (**51**, complete as of 2026-10-15, after `glucose_over_7` was deleted):
`badtime_tv`, `bedroom_dark`, `bedroom_door_closed_arms_sleep`, `bedroom_door_closed_settle_in`, `bedroom_door_opened_morning`, `bedroom_door_opened_night`, `bedroom_door_verified_shut`, `bedroom_night_exit_nightlight`, `bedroom_night_settled_reset`, `bedroom_wake_release`, `boiler_off`, `catio_at_dawn`, `catio_at_dusk`, `catio_door_indicator`, `catio_door_open_when_away`, `cattic_off`, `door_layer_alert`, `door_layer_cross_check`, `door_unlocked_too_long`, `headboard_kill_all`, `kitchen_motion`, `l40_clean_cat_box_on_litter_robot_cycle`, `library_pole_bedtime_fade`, `lights_on_basement`, `matt_bedtime_armed_reset`, `matt_bedtime_prep`, `matt_falls_asleep`, `matt_insulin_trip_arm`, `matt_leaves_bathroom`, `matt_lights_bathroom`, `matt_morning_macro_auto`, `matt_morning_macro_reset`, `matt_office_daytime_after_shower`, `matt_shower_detected`, `matt_shower_done_reset`, `mister_p_door_indicator`, `morning_boiler`, `office_light_status`, `omp_bedtime`, `sauna_door_cat_water_guard`, `sleep_cool_off`, `sleep_temp`, `sleep_trigger`, `steve_enters_home`, `steve_morning_greeting`, `turn_off_office_lights`, `turn_on_cattic_lights`, `turn_on_office_lights`, `tv_off_lights_out`, `water_meter`, `witness_watchdog_alert`.

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

- **`automation.llm_hooktest_1` — RESOLVED & DELETED 2026-10-10 (was a config-less registry orphan, not a YAML automation).** This was a "restored automation" *registry* entry (`unique_id: office_light_webhook`, `config_entry_id: null`, `device_id: null`) with **no body anywhere**: the REST config read returned 404 and `ha_config_remove_automation` returned `400 Resource not found` (HTTP `VALIDATION_FAILED`) because nothing existed at the config layer. **The earlier claim in this section — that its body "lives in `automations.yaml`" — was wrong:** the repo contains **no `automations.yaml`** at all (verified: `find . -name 'automations.yaml'` → no results, and `office_light_webhook` appears in only **2** of the **477** tracked files, both of them audit prose describing this now-deleted orphan — this doc and `wiki/agent-index.md` — never an automation body). **Correct cleanup path for this shape is the registry delete `ha_remove_entity("<entity_id>")`**, which succeeded; the config-remove API is a no-op/400 for a body-less orphan and must not be read as "already deleted". Post-fix verification: `ha_get_entity` → `Entity not found`; `ha_search("llm_hooktest_1")` → 0 entity matches + 0 config matches repo-wide (`partial: false`, `warnings: []`). **No blind spot remains in "scan all automations".**
- **`binary_sensor.bedroom_door` — magnet gap (fixed 2026-09-24; the physical mounting fix is permanent — a sensor-mount fix, not a software gate).** The contact only detected the magnet as it **swept past**, so a shut door read `on` and an `off → on` ("door opened") trigger fired on *closing* — switching off the bedroom night lights at 22:17:46 on 2026-09-23. After moving the magnet the door held `off` continuously for 2 min 51 s. **Guard claim corrected 2026-10-01:** `input_boolean.bedroom_door_verified_shut` is a **latch, not an enforced gate**. The `bedroom-door-verified-shut` automation *sets* it after the door reads `off` for 2 minutes; the door-open automations merely *test* it (`verified_shut = on` AND `night_settled = on` AND a time window). The earlier wording here — that it "requires the door to read `off` for 2 minutes before any 'door opened' automation will run" — described the *intent* and was never verified against runtime behaviour. Under the config loaded at 2026-10-01 08:52:35.866 that latch condition has **zero executions** (no post-reload door-triggered trace; `last_triggered` 08:38:05 predates the reload), and the latch is **consumed by the very door events it guards** then re-armed by the door's own 2-minute debounce. Full mechanic + trace evidence in §5. A plain duration debounce on `on` does **not** work here — after a glitch the state stays `on`. Bedroom logic (`bedroom-door-…` are the automations' **aliases**; the live `entity_id`s use underscores): `automation.bedroom_door_verified_shut`, `automation.bedroom_door_opened_night`, `automation.bedroom_door_opened_morning`, `automation.bedroom_door_closed_settle_in`, `automation.bedroom_night_settled_reset`; the three earlier attempts are present but switched **off** at runtime — registry `enabled: true`, `disabled_by: null`, i.e. **not** registry-disabled (re-verified 2026-10-10) — `automation.bedroom_door_closed_arms_sleep` and `automation.bedroom_night_exit_nightlight` (`last_triggered` 2026-09-24 04:58 local) and `automation.bedroom_wake_release` (`last_triggered` 2026-09-24 11:55 local). Details: [zigbee-door-sensor-rollout.md](zigbee-door-sensor-rollout.md) § Incident log.
- **`scene.daytime` whitens the 2nd-floor lights.** It sets `light.bulb_secondfloor_stair_hallway` (5000 K @199) and `light.bulb_masterbath_ceiling_light` (5000 K @184), applied by `automation.matt_office_daytime_after_shower` — so a night-time red night path can jump to bright white when that chain fires.
- **`mwave-basement` is battery-powered** — battery mmWave can be slow to trigger/clear; prefer mains for "hold the lights" duty.
- **mmWave false-positives** from heat/fans: keep basement mmWave pointed away from the boiler and vents, mount high and angled down.
- **Node-RED** add-on is stopped and being considered for removal; flows are deleted on uninstall — back up first. No HA-side references to it.
- **`light.bulb_living_tablelamp` has exactly one writer — `automation.catio_door_indicator` (verified 2026-10-13).** It renders a three-state precedence: **red** `rgb 255,0,0` @100 % = front door (`lock.termite_towers`) unlocked; **amber** `rgb 255,40,0` @40 % = either catio-access contact open (`binary_sensor.catio_door` or `binary_sensor.cat_door`); **green** `rgb 58,255,47` @36 % = all clear. Two traps worth knowing before touching it: (a) `automation.glucose_over_7` used to drive this lamp by **device id** (`1271c800e7c03abe59660ffcf3b81b1e`, `type: flash`), which an entity-id grep does **not** reveal — it was deleted 2026-10-13 (`unique_id 1775864309612`), so any new lamp writer must be added deliberately and audited by device UUID as well as entity id; (b) red and amber are near-identical hues (0° vs 9.4°) separated **only by brightness** (100 % vs 40 %), so do not "tidy" red's brightness down to match amber — the precedence would disappear. `binary_sensor.cat_door` (cat door behind the shelf, paired 2026-10-13) had **unverified polarity** until the magnet was **physically adjusted** on 2026-10-13; the contact then produced its first sustained states — **9 h 25 m `on` overnight** and **3 h 47 m `off` the next morning** — which corroborate the standard `off` = closed mapping. It is now **chattering**, though: most of its **85 rows in 30 h** are off/on pairs 0.2–4.5 s apart, the same marginal-magnet-gap signature `bedroom_door` had before its 2026-09-24 magnet move, and every edge fires the indicator. Details: [zigbee-door-sensor-rollout.md](zigbee-door-sensor-rollout.md) § Verification note 2026-10-13 + § Update 2026-10-14.
- **`light.mister_p_rgbcw_lightbulb` has exactly one writer — `automation.mister_p_door_indicator` (created 2026-10-14).** Second indicator lamp (Tuya local, Living Room, `hs` + `color_temp`). Before this it had **zero** writers — which is literally why its owner reported it "did not change colour". Three states: **red** `rgb 255,0,0` @100 % = front door unlocked, always, no time gate; **yellow** `rgb 255,200,0` @60 % = a catio-access contact open **and dark**; **green** `rgb 58,255,47` @36 % = otherwise. Three things to know before touching it: (a) **green also covers "a catio door is open, but it is daytime"** — those doors are open by design all day, so a daytime open door is deliberately *not* flagged, and green means "no action required" rather than "all closed" (do not un-gate yellow — that is the amber-all-day problem, and the time box was an explicit owner request); (b) it carries **`sun` triggers on `sunset` and `sunrise`** in addition to the door/lock triggers, because the yellow/green verdict depends on the sun — without them a door already open at nightfall would never turn yellow nor return to green at dawn, and HA's sun trigger offers **only** `sunset`/`sunrise` (there is no native `dusk` trigger), so the `condition: sun` is aligned to `after: sunset` / `before: sunrise` to keep trigger and condition on identical edges; (c) it does **not** touch `light.bulb_living_tablelamp`, which keeps its own red/**amber**/green scheme — the two lamps intentionally use **different** middle colours (amber `255,40,0` vs yellow `255,200,0`).
- **Anonymous room sensors cannot tell Matt from Steve — the morning chain now carries an explicit `insulin_trip` identity latch (2026-10-15).** `binary_sensor.mwave_masterbath_sink_presence` and `sensor.mwave_masterbath_sink_humidity` are anonymous, and `person.*` is GPS/zone-level only (never room-level), so the *first* morning event used to win regardless of who it was. On 2026-10-15 a **Steve** bathroom break (bedroom door 05:00:43 → sink 05:00:54.067, one 103 s burst, **zero** kitchen activity) consumed `input_boolean.matt_morning_macro_fired`, and Matt's genuine 06:25:18 entry got nothing. The discriminator is **`binary_sensor.refrigerator_door`** — Matt's step 2 is an insulin grab from the **downstairs Kitchen** fridge (routine step 2 *is* the grab), which Steve's route never touches. Chain now: `automation.matt-insulin-trip-arm` latches `input_boolean.matt_insulin_trip` on a fridge opening **04:30–09:00** (plus a **60 s sustained** `mwave_kitchen_presence` dwell as an LG Thinq **cloud**-outage fallback); **both** `automation.matt-morning-macro-auto` and `automation.matt_shower_detected` now require that latch, and `automation.matt_morning_macro_reset` clears it at midnight with the macro latch. The fridge preceded the 65 % humidity crossing on 3/3 mornings checked, so the precondition costs nothing on a real Matt morning. Two things to keep in mind: (a) the sink sensor is **still** anonymous, so if Matt uses the bathroom *before* his insulin grab (seen 2026-10-13) the macro fires on his **second** sink entry — a 1–2 min delay, never a miss, which is why the macro window was deliberately left at **05:00** rather than bumped to 05:30 (the fridge gate, not the clock, discriminates); (b) the 60 s kitchen fallback is **not** person-specific, so delete that trigger from `matt-insulin-trip-arm` if a false arm is ever observed. `automation.matt_office_daytime_after_shower` additionally gained a **05:00–12:00** window so a stale `matt_shower_done` flag cannot apply `scene.daytime` in the evening. **The identity half of this bug class remains open on `automation.steve_morning_greeting`** — as of 2026-10-18 it no longer triggers on the raw `mwave_1stbath_presence` but on the 45 s-debounced `mwave_1stbath_presence_confirmed`, so walk-by traffic can no longer eat the once-a-day latch; the sensor is *still* anonymous, though, and a "not Matt" gate was **explicitly deferred by the owner** (see [routines.md §5](routines.md)). **Also open: `media_player.bathroom_speaker` (Cast, 192.168.4.43:8009) has been `unavailable` since 2026-10-14 11:11:27** — ARP `FAILED`, ICMP unreachable, TCP 8009 "No route to host", while `.34`/`.35` Cast displays answer on the same port; the device is powered off or off Wi-Fi and nothing in HA can restore it, so the morning macro is currently **lights-only**. Both automations that cast to it carry `continue_on_error: true` so it cannot abort a sequence.

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

