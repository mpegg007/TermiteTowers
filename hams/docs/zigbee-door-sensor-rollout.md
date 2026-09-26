<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: hams/docs/zigbee-door-sensor-rollout.md:156 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: 729c06384eb9b2604f960ab514bd09e24d665aeb % -->
<!-- %ccm_git_commit_id: 7297d224e38a7887c494edb01cda0f8167185bf0 % -->
<!-- %ccm_git_commit_count: 156 % -->
<!-- %ccm_git_commit_date: 2026-09-25 20:27:36 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: cleanup % -->
<!-- %ccm_git_modify_date: 2026-09-25 20:27:36 % -->
<!-- %ccm_git_file_last_modified: 2026-09-25 17:19:57 % -->
<!-- %ccm_git_file_name: zigbee-door-sensor-rollout.md % -->
<!-- %ccm_git_path: hams/docs/zigbee-door-sensor-rollout.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: utf-8 % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 26090 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# Zigbee door/contact sensor rollout

> **What this is:** the working plan *and* live status for deploying the spare
> Zigbee contacts, PIRs and button into HAL — which opening each one goes on,
> what automation each one buys, and the naming contract that lets you pair them
> in any order.
>
> **What this is NOT:** an authority for entity state. Entity IDs, states,
> availability and battery levels must always be queried live via `hal-mcp`.
> This file records **intent and design rationale**; query HAL for truth.

- **Created:** 2026-09-23
- **Status:** in progress — 3 contacts deployed, 1 spare, 5 devices pending
- **Related:** [hal-context.md](hal-context.md) (instance snapshot) · [SKILL.md](SKILL.md) · `hams/inventory/`

## Status at a glance

| # | Device | Opening | Intended entity | State |
|---|---|---|---|---|
| 1 | Contact — SONOFF | **Bedroom** interior door | `binary_sensor.bedroom_door` | ✅ deployed — magnet moved, reworked automations live (see incident log) |
| 2 | Contact — SONOFF | **Catio** lower deck door (off the Laundry) | `binary_sensor.catio_door` | ✅ deployed + automated |
| 3 | Contact — SONOFF | **Sauna** door | `binary_sensor.sauna_door` | ✅ deployed + automated |
| 4 | Contact | **Front door** (Entry) | `binary_sensor.front_door` | ⬜ not paired |
| 5 | Contact | Master bedroom → Catio **upper deck** | `binary_sensor.deck_door` | ⬜ not paired |
| 6 | Contact | — | **spare, still in the box** | ⬜ unassigned |
| 7 | PIR | **2nd Hallway** / stair landing | `binary_sensor.pir_2ndhall_occupancy` | ⬜ not paired |
| 8 | PIR | **Master Bath** | `binary_sensor.pir_masterbath_occupancy` | ⬜ not paired |
| 9 | Button | Second nightstand | `button-bedhead-steve` | ⬜ not paired |

The spare's named future homes: the **winter cat door behind the shelf** (Laundry
side of the Catio), or a **window**, or the deck door's **screen leaf** if the
winter-cooling signal ever matters enough to spend two sensors on it.

## Naming contract — pair in any order

**Pairing order does not matter. Physical placement does.** Automations bind to
entity IDs, so you can pair devices over as many sessions as you like, in any
sequence.

Two rules make that work:

1. **Z2M name** → the device friendly name, in the `<Type>.<place>` convention
   (`Bedroom.door`, `Catio.door`, `Sauna.door`).
2. **HA entity ID** → renamed to the short form in the table above. Z2M's
   auto-generated ID carries a redundant suffix
   (`binary_sensor.bedroom_door_contact`); rename it **before** writing
   automations, because Home Assistant does **not** propagate entity renames into
   automations, scripts or dashboards.

```text
ha_set_entity("binary_sensor.<name>_door_contact", new_entity_id="binary_sensor.<name>_door")
ha_set_device("<device_id>", area_id="<bedroom|catio|sauna|entry>")
```

Set the **device** area (not just the entity) so the battery/linkquality entities
inherit it. Then confirm polarity before automating.

### Polarity — verify, don't assume

SONOFF contacts arrive with `device_class: door`, and HA's convention for that
class is **`on` = open, `off` = closed**. Verify by closing each door: if a
physically-closed door reads `on`, the magnet is on the wrong side. Fix by
rotating the magnet, or swap `to: "on"` / `to: "off"` in the triggers.

As of this writing all three deployed contacts read `on` (open) — consistent with
the sauna door, which is normally open for the cat water bowl.

## Design rule: no panic

Stated preference: *"last thing I want is a panic from a text telling me the
front door is open."*

> **Contacts drive behaviour and quiet logging. A mobile notification is
> reserved for *unattended* or *impossible* states, and carries a camera snapshot
> where one exists.** Nothing texts you merely because a door is open.

This is why the Catio door reports through a **lamp colour** rather than a
notification, and why the front door plan is built around a silent logbook entry
plus an "ajar while locked" alert instead of an open-door text. HAL has **no
alarm panel** (`alarm_control_panel` is empty), so door contacts are the only
"something to the outside is open" signal that can exist.

## Live entities deployed so far

| Entity | Device | Area | Notes |
|---|---|---|---|
| `binary_sensor.bedroom_door` | `Bedroom.door` (SONOFF, `0xa4c13881970be516`) | `bedroom` | renamed from `..._bedroom_door_contact` |
| `binary_sensor.catio_door` | `Catio.door` (SONOFF, `0xa4c13849ae8c0a3a`) | `catio` | Laundry ↔ Catio lower deck |
| `binary_sensor.sauna_door` | `Sauna.door` (SONOFF, `0xa4c138d17e20fd58`) | `sauna` | |
| `binary_sensor.anyone_home` | template helper | — | `{{ is_state('person.matthew','home') or is_state('person.steve','home') }}` |
| `binary_sensor.bedroom_asleep` | template helper | — | `{{ is_state('binary_sensor.bedroom_door','off') and (now().hour >= 21 or now().hour < 6) }}` |

Each contact also exposes `sensor.<name>_battery`, `sensor.<name>_voltage`,
`binary_sensor.<name>_battery_low` and a linkquality sensor.

`binary_sensor.anyone_home` exists so automations can use a native
`condition: state` instead of a template. `person.*` states are `home`, a zone
name, or `not_home` — so `state: not_home` silently fails when someone is in a
named zone (e.g. at work). The helper checks the home zone specifically.

## Automations built

| Automation | Trigger | Behaviour |
|---|---|---|
| `automation.catio_door_indicator` | `binary_sensor.catio_door` on/off/restart | `light.bulb_living_tablelamp` → **amber** (`rgb 255,40,0` @40 %) while the door is open, **green** (`rgb 58,255,47` @36 %) when closed. Explicit colours — no scene snapshot (see incident log) |
| `automation.catio_door_open_when_away` | door open `for: 5 min` | + `anyone_home` off → notify `notify.sm_s911w` with a Catio camera snapshot attached |
| `automation.bedroom_door_closed_arms_sleep` | `binary_sensor.bedroom_door` → `off` | 21:00–06:00 → `input_boolean.matt_bedtime_armed` on |
| `automation.bedroom_night_exit_nightlight` | bedroom door `off` → `on` | 21:00–06:00 → dim red path (`light.bulb_secondfloor_stair_hallway` @50 %, `light.bulb_masterbath_ceiling_light` @20 %) and bedroom night lights off |
| `automation.bedroom_wake_release` | bedroom door `off` → `on`, or 11:55 sweep | 05:00–12:00 → clear `matt_bedtime_armed` + `matt_bedtime_prep` |
| `automation.sauna_door_cat_water_guard` | `binary_sensor.sauna_door` → `off` `for: 20 min` | + `sensor.sauna_temp_probe_temperature` below 40 → notify. Heated = silent |

Indicator colours: **amber** `rgb 255,40,0` @40 % = door open; **green**
`rgb 58,255,47` @36 % = the lamp's normal look (used only by the restart-recovery
branch). The lamp was chosen because nothing else in HAL referenced it.

### Incident log — 2026-09-24 (first night)

The first night of live bedroom automation produced three faults. All three bedroom
automations were **turned off** the next morning; the catio and sauna logic stayed live.

**1. The bedroom contact's closed resting state reads `on` (open).** Across 19:00–18:00 it
logged 19 entries: `on` by default, with **nine** `off` events — eight of them sub-second,
plus one sustained `off` of 2 h 13 m:

```text
22:17:45.229 off  ->  22:17:45.499 on     (270 ms)   <- the close that killed the lights
01:02:11.946 off  ->  01:02:12.176 on     (231 ms)
01:03:28.904 off  ->  01:03:29.056 on     (152 ms)
02:42:40.718 off  ->  02:42:40.881 on     (163 ms)
02:42:56.330 off  ->  04:56:35.229 on     (2 h 13 m 39 s)  <- the one sustained closed
04:58:04.408 off  ->  04:58:04.635 on     (227 ms)
06:17:35.168 off  ->  06:17:35.896 on     (728 ms)
06:17:41.020 off  ->  06:17:41.359 on     (339 ms)
07:22:49.262 off  ->  07:22:49.501 on     (239 ms)
```

Consequence: an `off -> on` trigger ("the door was closed and is now open") fired
**when the door was closed**, because closing it produces the blip. The 22:17:45 blip
switched off `light.tl_bedroom_rgbcw_lightbulb2` and `light.bulb_bedroom_pole_lower` 0.64 s
later — the two bulbs `matt-leaves-bathroom` had set green only 4.5 minutes earlier.

**The bathroom trips prove the point.** Master-bath mmWave occupancy lines up with door
events all night, but the door reports each trip as one or two sub-second `off` pulses —
never as a sustained open/close pair:

| Master bath occupied | Door activity | Lag |
|---|---|---|
| 22:12:00 – 22:14:13 (pre-bed visit; `matt-leaves-bathroom` fired 22:13:20) | `off` 22:17:45.229 -> `on` .499 (270 ms) | door shut **3 m 32 s** after leaving the bathroom |
| 01:02:26 – 01:02:57 and 01:03:11 – 01:03:41 | `off` 01:02:11.946 -> `on` .176 (231 ms); `off` 01:03:28.904 -> `on` .056 (152 ms) | 15 s before the first burst; inside the second |
| 04:57:02 – 04:57:32 and 04:57:45 – 04:58:15 | `on` 04:56:35.229 (ends the 2 h 13 m `off`); `off` 04:58:04.408 -> `on` .635 (227 ms) | door opened **27 s before** the bathroom burst |
| 06:19:29 – 06:20:55 (+ bursts to 06:28) | `off` 06:17:35.168 -> `on` .896 (728 ms); `off` 06:17:41.020 -> `on` .359 (339 ms) | ~2 min before the first burst |
| 07:10 – 07:31 morning activity | `off` 07:22:49.262 -> `on` .501 (239 ms) | inside the cluster |

So the contact **is** detecting the door moving on every trip — it just cannot hold the
closed state. That is the signature of a magnet gap sitting **at the edge of the contact's
range**: the shut position is a hair too far, so `on` is reported whether the door is open
*or* shut, and `off` appears only when a swing momentarily brings the halves closer, or when
the door happens to rest where the gap holds.

**Door-cycling session, 2026-09-24 17:29–17:32** — door deliberately opened/closed repeatedly,
producing six `off` events (bedroom mmWave confirms the user was present):

```text
17:29:08.720 off -> .769 on     (  49 ms)
17:29:17.718 off -> 17:29:20.142 on   (2.42 s)
17:29:22.543 off -> .702 on     ( 159 ms)
17:29:39.133 off -> .258 on     ( 125 ms)
17:31:49.737 off -> .856 on     ( 119 ms)
17:31:58.133 off -> .258 on     ( 125 ms)
17:34:03.697 off -> .776 on     (  79 ms)
17:34:11.736 off -> .874 on     ( 138 ms)
```

Across the whole 3-hour session there were **eight** `off` events and **none exceeded 2.42 s** —
including the deliberate single-close attempt at 17:34. The missing piece is that logs cannot show
whether the door was *left* shut between attempts or re-opened each time.

**Settled — the magnet sweeps past the contact.** The door's intent for each pair was confirmed:
at **17:34** the door was **closed at 17:34:03.697** and **re-opened at 17:34:11.736** — shut and
untouched for **8.0 s** — and at **17:31** closed 17:31:49.737 → opened 17:31:58.133, shut for
**8.4 s**. In both intervals the contact read `on` (open) for essentially the whole time, emitting
only a sub-150 ms `off` pulse at the moment of closing and another at the moment of opening.

So the contact *does* detect the magnet — but only as it **sweeps past**. The settled closed
position is outside the magnet's range. That explains the overnight data (each trip's movement
produced pulses while the resting closed state read `on`) and why `binary_sensor.bedroom_asleep`,
which requires the door `off`, was effectively never true at night. The one anomaly remains the
sustained **2 h 13 m `off`** on 02:42:56 – 04:56:35, when the gap evidently did hold.

Note also that a plain duration debounce on `on` would **not** have prevented the original
misfire: after the 125 ms blip the state stays `on` for minutes, so waiting longer proves nothing.
Only a "was it verifiably shut first?" gate works.

*Fix (physical):* bring the magnet into range at the **closed resting position**. Practical order:
hold the magnet half directly against the sensor to establish the distance at which it reads `off`
and holds it, then reproduce that distance with the door shut — usually a spacer behind the magnet
half, or re-mounting it on the door face instead of the frame edge. If the frame depth makes that
impossible, a sensor with a deeper magnet gap (or a hinge-side mount) is the answer. Verify by
closing the door and leaving it untouched: `off` must hold for the whole time it is shut.

**Fixed — 2026-09-24.** The magnet was moved. The `off` durations grew as it came into range
(1.8 s, 2.6 s, 4.2 s, 11.6 s, 24.2 s, 10.3 s), and the door then read `off` **continuously for
2 min 51 s** (17:47:06 → 17:49:57) with the room empty — the first sustained shut reading in three
hours, where previously no `off` exceeded 2.42 s. The contact now reports the closed position.

### The gate and the reworked bedtime choreography (live from 2026-09-24)

Because `on` had been the default, a plain duration debounce on `on` is **not** sufficient — after a
glitch the state *stays* `on`, so waiting longer proves nothing. The gate therefore runs the other
way round: **an opening only counts if the door was verifiably shut first.**

| Entity | Role |
|---|---|
| `input_boolean.bedroom_door_verified_shut` | Set only once the door has read `off` for **2 minutes**; cleared by whichever open-handler runs. Every "door opened" automation requires it. |
| `input_boolean.bedroom_night_settled` | Latched by the settle-in so the bedtime scene fires **once per night** |

| Automation | Trigger → behaviour |
|---|---|
| `automation.bedroom_door_verified_shut` | door `off` held 2 min → arm the gate |
| `automation.bedroom_door_opened_night` | door `on` + gate + 21:00–06:00 → night path (stair ceiling, master-bath ceiling, under-sink) to **very dim red 8 %**; clears the gate. **No longer switches bedroom lights off** |
| `automation.bedroom_door_opened_morning` | door `on` + gate + 05:00–12:00 → night path to **dim orange 30 %** — a step up from dark red instead of the jump to `scene.daytime`'s 5000 K white; clears the gate and the settle latch |
| `automation.bedroom_door_closed_settle_in` | door `off` held 5 s + 21:00–06:00 + someone in the room + room lit + not already settled → `scene.mpegg_bedtime_tv` (green bedroom + TV), night path to very dim red, **library pole off**, latch the settle flag |
| `automation.bedroom_night_settled_reset` | 12:00 daily → clear the settle latch and the gate |

The settle-in requires *both* "someone in the room" and "the room is lit", and latches once per
night, so a 3 a.m. bathroom return cannot switch the TV on. Its green-bedroom + TV-on half is the
same scene `matt-leaves-bathroom` already applies, so the door close re-asserts that look rather
than introducing a new one.

**Superseded, left disabled (not deleted):** `bedroom-night-exit-nightlight` (its bedroom-light-off
action is the design flaw in item 4), `bedroom-door-closed-arms-sleep` (duplicated
`matt-leaves-bathroom`'s arming and moved the timing earlier) and `bedroom-wake-release` (folded
into `bedroom-door-opened-morning`).

### First-night review — 2026-09-25 (passed)

The magnet fix held. The door shows genuine sustained closed states overnight — **3 h 15 m**
(21:35:04–00:50:37), 1 h 8 m, 3 h 13 m, 51 m, 35 m — with short opens (1 m 19 s, 5 s, 1 m 14 s, 6 s)
for trips. That is the correct signature, and the opposite of the pre-fix pattern.

| Time (EDT) | What fired | Result |
|---|---|---|
| 21:35:09 | `bedroom-door-closed-settle-in` (door shut 21:35:04 + 5 s) | ✅ ran — the night's only settle; latched `bedroom_night_settled` |
| 00:50:37 | `bedroom-door-opened-night` | ✅ dim red path — bedroom lights untouched |
| 02:00:17 | `bedroom-door-opened-night` | ✅ same |
| 05:13:56 | **both** night and morning | ⚠️ window overlap — fixed below |
| 05:15:15 | `bedroom-door-closed-settle-in` | ✅ correctly blocked (latch set + room empty) |
| 06:06:28, 06:41:40 | `bedroom-door-opened-morning` | ✅ orange step; night branch correctly failed |

The latch did its job: every re-close after the settle was blocked, so there was no repeat TV-on at
00:52, 02:00 or 05:15. And nothing switched bedroom lights off at any point — the 2026-09-23 fault
is gone.

**Defect found and fixed (mine):** `bedroom-door-opened-night` (21:00–06:00) and
`bedroom-door-opened-morning` (05:00–12:00) **overlapped between 05:00 and 06:00**, so at 05:13:56
*both* ran — two automations writing the night path in a race, with the final colour decided by
millisecond ordering. The windows are now split at **05:30**, taken from `routines.md` ("leave
bedroom after 5:30am"): a pre-05:30 exit is a night trip (dim red) and the wake step waits for the
real morning.

**Known conflicts, found while investigating an unrelated 5 a.m. report.** (The user had turned the
bathroom lights off manually, so no fault — but the exposure is real.) The master-bath powerbar
(`tl.USB 4way powerstrip`, Tuya) has its outlets in several off-lists:

| Automation / scene | Effect on that powerbar |
|---|---|
| `tv-off-lights-out`, `headboard-kill-all` | turn off all five powerbar entries |
| `scene.mpegg_bedtime_tv` | both light wrappers → off |
| `scene.daytime` | `light.tl_usb_4way_powerstrip_outlet_1_2` → off (observed live: `Daytime` activated 07:01:17, `switch...outlet_1` off at 07:01:18) |
| `bedroom-sleep-now` (disabled) | off |

So anything the morning macro switches on there can be killed by a TV-off or by the Daytime scene.
The naming on that device is also crossed — switches `outlet_1`/`outlet_2` are "sink light"/"main
lights" while wrappers `_2_2`/`_1_2` are "sink lights"/"main lights" — which is how a scene ends up
switching the "wrong" one. Left as-is by request; recorded so it is not rediscovered.

Once it reads correctly, re-enabling the bedroom automations needs the **"verifiably shut" gate**
(believe an opening only if `off` held ≥2 min immediately before it) as well as the reworked
door-*close* sequence — see item 4.

*Design guard (software, regardless of hardware):* never let a sub-second edge run an
action. Because this unit's `on` is the default, a plain duration debounce on `on` is not
sufficient; the robust rule is to believe an *opening* only when the door had been
**verifiably shut** (`off` held for ≥2 min) beforehand.

**2. Arming moved earlier than the tuned bedtime moment.**
`bedroom-door-closed-arms-sleep` armed `input_boolean.matt_bedtime_armed` on door close,
but `matt-leaves-bathroom` already does that at the right point in the sequence. Arming
on door close let the wind-down fire on whatever light turned off next, and with the
sensor blipping it also armed at 02:42 and 04:58. Disabled — the original timing is restored.

**3. The catio indicator pinned the lamp amber.** The original design snapshotted the lamp
with `scene.create` and then overwrote it with amber. At 07:42:39 the restore commanded
228 ms earlier was **still in flight over Zigbee**, so the snapshot captured *amber* as
"normal" and every later restore re-applied amber. The lamp sat amber for hours.

*Fix (in place):* the indicator now writes explicit colours — amber when the door is open,
green when closed — reading the door's **current** state, so it is idempotent and has no
snapshot to corrupt.

**4. The night-exit design was wrong on its own terms.** `bedroom-night-exit-nightlight` switches the
bedroom night lights **off** whenever the door opens at night. If the door genuinely opened (bounced
back open, or was re-opened), the automation did exactly what it was told — and still darkened the
room. Turning lights off on a door-open is the wrong response for this house: the intent was "don't
flash whoever is still in bed", but killing all three bedroom bulbs also destroys the green bedtime
scene. This needs reworking as part of the door-*close* sequence, not as an open-triggered switch-off.

**Not caused by this rollout, but seen that same morning:** `scene.daytime` sets
`light.bulb_secondfloor_stair_hallway` (5000 K @199) and `light.bulb_masterbath_ceiling_light`
(5000 K @184) — bright white. It is applied by `automation.matt_office_daytime_after_shower`
once the shower + office-entry chain completes, which is what lit the hallway and bathroom
white. Pre-existing behaviour; this rollout never touched it.

### Deferred — read why before rebuilding

| Plan item | Status | Reason |
|---|---|---|
| Catio door → patio lights | **dropped** | `catio_at_dawn` / `catio_at_dusk` already run `switch.energy_monitoring_smartplug` (patio lights) sunset → sunrise, so the door adds nothing |
| Bedroom "closed but empty" overnight guard | **deferred** | Needs reliable presence. The bedroom mmWave logged **156 state changes in 24 h with overnight gaps up to ~18 min** (e.g. off 03:14:18 → on 03:31:58), so any "no presence for N minutes" guard would false-fire. Tune `number.mwave_bedroom_fading_time` (currently 30 s) / sensitivity first, or accept a much longer threshold |
| Presence clause in `bedroom_asleep` | **removed** | HA's template-helper flow **rejected `delay_off`** ("keys not declared by the schema") at 2026.9.2, so a presence-based derivation cannot latch and would flicker with the mmWave. Door + time is stable and matches the "door is closed when we sleep" model |
| Battery-low alerts for the 3 contacts | **not built** | The `*_battery_low` entities exist and are `off`; one quiet notifier is better than three. Pairs naturally with the front-door lock battery alert. Plan item, no urgency on fresh batteries |

## Planned (not yet built)

- **Front door (Entry)** → `binary_sensor.front_door`. The quiet set: *ajar while `lock.termite_towers` reports `locked`* (a U-Bolt has **no door-position sensor** and is a **SmartThings cloud** device, so "locked but not latched" is invisible today) → notify + `camera.front_door_live_view` snapshot; *opens 23:00–06:00 with `anyone_home` off* → notify + Ring snapshot; *same window with someone home* → **`logbook.log` only, zero notifications**; plus patching `door_layer_cross_check` to use a local sensor instead of two cloud ones.
- **Deck door (upper deck, off the bedroom)** → quiet announce after 30 min open with the bedroom empty. A single contact cannot distinguish "winter cooling by design" from "left open" — that needs the **main + screen pair**.
- **PIR #1 → 2nd Hallway**, **PIR #2 → Master Bath**.
- **`button-bedhead-steve`** → added as an extra trigger to the existing `bedroom.sleep.now`, `badtime.tv` and `headboard-kill-all` (today the entire bed-gesture system is `button-bedhead-matt` only).
- **A generic `doors-open-while-away`** across all contacts, `for: 2 min`.

## House facts that shaped the plan

- **Catio = fenced-in back yard** (the cat patio); **Cattic = the attic**, another cat play room.
- The catio is **two floors**: lower deck off the **Laundry** (the "main catio door"), upper deck off the **master bedroom**. The cats can nudge the main door open if it is not latched. A **shelf beside it opens the cat door**, so in winter the main door can stay shut.
- **Only the sauna door can block the cats.** Both Green Room sliding barn doors (to the sauna/1st bath and to the laundry) have **cat cutouts**; the master bath door is never closed. The barn doors are closed only when it is cold.
- The **Catio door is from the Laundry**, and the Laundry has a working Echo (`media_player.laundry_mpegg_s_echo_pop`). `laundry_echo_input` is `unavailable`.
- Bedroom has a **second opening** — the upper-deck door — which is **open by design in winter** with the screen door closed. Sleep logic therefore keys on the **interior** door only.
- Sauna has **no light or switch**; the only signals are the door contact and `sauna-temp` (probe, `number.sauna_temp_sampling_interval` = 600 s), which is why the contact is the instant signal there.

## Commissioning procedure for the remaining devices

1. **Back up first** — `ha_manage_backup(scope="snapshot", action="create")`.
2. Pair **one at a time beside the coordinator** (it lives in `office`) so the
   device does not latch onto a far router, then relocate it. Permit join via
   `switch.zigbee2mqtt_bridge_permit_join` or the Z2M sidebar panel.
3. Rename in Z2M → `ha_set_entity(new_entity_id=…)` → `ha_set_device(area_id=…)`.
4. **Verify polarity** by opening and closing the door, then read the state.
5. Check `sensor.<name>_battery` and linkquality in the final location. Two mains
   routers are available and unplaced (`Plug-basement-gen3`,
   `Plug-cabinet-fisrtstairs`) if a spot reads weak.
6. Only then write automations that reference the new entity IDs.

## Verification commands

```text
ha_get_state               ["binary_sensor.catio_door","binary_sensor.bedroom_door","binary_sensor.sauna_door"]
ha_get_history             entity_ids="binary_sensor.catio_door", start_time="24h"
ha_get_automation_traces   "automation.catio_door_indicator"
ha_get_logs                source="logbook", entity_id="binary_sensor.catio_door"
```

## Follow-ups / open items

- **`sleep_temp` / `sleep_cool_off` are pure time+temp automations with no sleep
  input** (`sleep_temp`: every 10 min, bedroom temp above 15.5, 21:30–05:50 → cool;
  `sleep_cool_off`: every 15 min, below 14, 23:00–05:45 → heat).
  `bedroom_wake_release` therefore cannot "release" them; wiring a wake or door
  signal into the bedroom climate logic is a separate decision that needs a call
  on the desired behaviour.
- `matt_leaves_bathroom` still arms `input_boolean.matt_bedtime_armed` from the
  bathroom switch. `bedroom-door-closed-arms-sleep` is **additive** — the old
  proxy was left in place deliberately. Once door-based arming is trusted, remove
  that action from `matt_leaves_bathroom` so the door is the single source of truth.
- No battery-low alert exists for the three contacts or the U-Bolt lock.
- Windows remain HAL's largest blind spot: no alarm panel and no window contacts.
- `hams/inventory/` still holds a placeholder device file (example MACs), and the
  `snipeit` schema referenced by `hal-context.md` / `wiki/agent-index.md` **does
  not exist** in `ttdb`, so nothing machine-readable tracks spare hardware.
