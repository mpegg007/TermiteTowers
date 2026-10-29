<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: hams/docs/zigbee-door-sensor-rollout.md % -->
<!-- %ccm_git_object_id: hams/docs/zigbee-door-sensor-rollout.md@194 % -->
<!-- %ccm_git_commit_date: 2026-10-28 20:22:38 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: misc updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2026-10-10 mpegg docs(hal): correct stale audit facts against live HA -->
 <!-- %git_commit_history: 2026-10-08 mpegg  impl www from prd branch  -->
 <!-- %git_commit_history: 2026-10-05 mpegg  house layout + routines docs  -->
 <!-- %git_commit_history: 2026-09-25 mpegg  cleanup  -->
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
- **Status:** in progress — **4 contacts deployed** (cat door added 2026-10-13), **0 spares left**, 5 devices pending
- **Related:** [hal-context.md](hal-context.md) (instance snapshot) · [SKILL.md](SKILL.md) · `hams/inventory/`

## Status at a glance

| # | Device | Opening | Intended entity | State |
|---|---|---|---|---|
| 1 | Contact — SONOFF | **Bedroom** interior door | `binary_sensor.bedroom_door` | ✅ deployed — magnet moved, reworked automations live (see incident log) |
| 2 | Contact — SONOFF | **Catio** lower deck door (off the Laundry) | `binary_sensor.catio_door` | ✅ deployed + automated |
| 3 | Contact — SONOFF | **Sauna** door | `binary_sensor.sauna_door` | ✅ deployed + automated |
| 4 | Contact | **Front door** (Entry) | `binary_sensor.front_door` | ⬜ not paired |
| 5 | Contact | Master bedroom → Catio **upper deck** | `binary_sensor.deck_door` | ⬜ not paired |
| 6 | Contact — SONOFF | **Cat door** behind the shelf (Laundry side of the Catio) | `binary_sensor.cat_door` | ✅ deployed 2026-10-13 — the ex-spare; **polarity unverified** (see below) |
| 7 | PIR | **2nd Hallway** / stair landing | `binary_sensor.pir_2ndhall_occupancy` | ⬜ not paired |
| 8 | PIR | **Master Bath** | `binary_sensor.pir_masterbath_occupancy` | ⬜ not paired |
| 9 | Button | Second nightstand | `button-bedhead-steve` | ⬜ not paired |

The ex-spare went to the **winter cat door behind the shelf** (Laundry side of the
Catio) — the first of its three named candidate homes. A **window** and the deck
door's **screen leaf** remain unassigned, and all four contacts are now spent, so
any further contact work needs new hardware.

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

As of this writing all four deployed contacts read `on` (open) — consistent with
the sauna door, which is normally open for the cat water bowl.

**`binary_sensor.cat_door` is the exception to "verified".** It was paired on
2026-10-13 and has **never recorded a door transition** — every state row in its
history is `unavailable`/`unknown`/`on` availability churn around HA restarts,
with the flap open throughout. Its **polarity is therefore unverified**: the
`on` = open mapping is an assumption inherited from `device_class: door`, not an
observed fact. This matters live: `automation.catio_door_indicator` drives its
amber state off this contact reading `on`. Close that door once, watch the
transition, and only then treat it as known. (An earlier draft of this section
claimed the one reading was `on` at 17:11:11; the recorder shows 17:11:11 was
`unavailable`→`unknown`, i.e. the pairing itself, and the first `on` was
19:07:19. Corrected in the 2026-10-13 21:09 note below.)

**The cat door is not a swing door — its resting state is "open".** Operator
context 2026-10-13: it is a **drawbridge-style flap**, normally left **open** by
day and closed only at night (or when someone forgets to lower it). Two
consequences worth separating:

1. **A static read cannot settle polarity.** With an open-by-default door, an `on`
   reading is equally consistent with `on` = open and with `on` = closed — nothing
   has observed it in the closed position since it was paired. The decisive
   observation is the **transition on closing** it, not the open state: `off` on
   close ⇒ `on` = open, leave the automations alone; still `on` while physically
   shut ⇒ closed reads `on`, and the fix for *this* door is the magnet — **not** a
   trigger swap (see item 2 below).
2. **Amber-while-open is kept deliberately, not by oversight.** `catio_door` is a
   human door that *should* be shut; the cat door is *supposed* to be open all day,
   so the shared amber branch holds the lamp amber for most of the day and starves
   the green "all clear" state. That consequence was put to the owner on 2026-10-13
   and **accepted**: the amber logic stays exactly as written. Consequence for the
   polarity test — an inverted sensor is fixed at the **sensor** (rotate the magnet),
   **not** by swapping `state: "on"` for `state: "off"` in the automation, which
   would silently invert the lamp's meaning rather than correct the reading.

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
| `binary_sensor.sauna_door` | `Sauna.door` (SONOFF, `0xa4c138d17e20fd58`) | `sauna` | swings into the narrow **1st bath** (Sauna ↔ Green Room is a **wall**, no opening) |
| `binary_sensor.cat_door` | `lower.cat.door.sensor` (SONOFF, `0xa4c13890c8c6fe04`) | `catio` | cat door behind the shelf; paired 2026-10-13, renamed from `binary_sensor.lower_cat_door_sensor_contact`; **polarity unverified**; device name not yet conformed to the Z2M `X.door` convention |
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
| `automation.catio_door_indicator` | `binary_sensor.catio_door` **and** `binary_sensor.cat_door` on/off, `lock.termite_towers` to/from `unlocked`, plus `homeassistant` start | **Single writer** for `light.bulb_living_tablelamp`. Precedence: **red** (`rgb 255,0,0` @100 %) = front door unlocked; **amber** (`rgb 255,40,0` @40 %) = either catio-access contact open; **green** (`rgb 58,255,47` @36 %) = all clear. Explicit colours — no scene snapshot (see incident log) |
| `automation.catio_door_open_when_away` | door open `for: 5 min` | + `anyone_home` off → notify `notify.sm_s911w` with a Catio camera snapshot attached |
| `automation.bedroom_door_closed_arms_sleep` | `binary_sensor.bedroom_door` → `off` | 21:00–06:00 → `input_boolean.matt_bedtime_armed` on |
| `automation.bedroom_night_exit_nightlight` | bedroom door `off` → `on` | 21:00–06:00 → dim red path (`light.bulb_secondfloor_stair_hallway` @50 %, `light.bulb_masterbath_ceiling_light` @20 %) and bedroom night lights off |
| `automation.bedroom_wake_release` | bedroom door `off` → `on`, or 11:55 sweep | 05:00–12:00 → clear `matt_bedtime_armed` + `matt_bedtime_prep` |
| `automation.sauna_door_cat_water_guard` | `binary_sensor.sauna_door` → `off` `for: 20 min` | + `sensor.sauna_temp_probe_temperature` below 40 → notify. Heated = silent |

Indicator colours: **red** `rgb 255,0,0` @100 % = front door unlocked;
**amber** `rgb 255,40,0` @40 % = either catio-access contact open; **green**
`rgb 58,255,47` @36 % = the lamp's normal look, and the restart-recovery branch.
The lamp was chosen because nothing else in HAL referenced it — and as of
2026-10-13 `automation.catio_door_indicator` is its **only** writer (see the
2026-10-13 note at the end of this file).

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

`bedroom-sleep-now` belongs in that list too, and for a sharper reason than the other three: it
shared a **byte-identical trigger** with `headboard-kill-all` — `device_id:
13679e4c48ddb27fb80f0fecb9a6af0f`, `subtype: single`, `conditions: []` — so the two could never both
be enabled. One press of the bed gesture would have fired both.

**Corrected 2026-10-10 (live-verified): `bedroom-sleep-now` was *deleted*, not left disabled.** It
is absent from the live automation roster (50 automations; `ha_search("bedroom_sleep_now")` → 0
entity + 0 config matches; `ha_get_entity` → `Entity not found`), so the shared-trigger hazard is
gone rather than merely suppressed. The "never re-enable it" advice below is therefore moot — there
is nothing left to re-enable.

The two are not twins, they are successive versions. `bedroom-sleep-now` carried id
`1775354224079` (≈ 2026-04-04) and `headboard-kill-all` id `1789083976341` (≈ 2026-09-10) — about
159 days apart — and `headboard-kill-all` is a **functional superset that absorbed it**: every light
and area `bedroom-sleep-now` turned off, `headboard-kill-all` also turns off (plus the Green Room
table light, `light.smart_light_23061297829567590a0148e1e9ca187f`, the office/library cluster, the
other powerbar outlets and `switch.tl_simple_switch`). The live `headboard-kill-all` `description`
confirms the absorption: *"Merged from bedroom.sleep.now: adds the Green Room table light
(`light.plug_green_tablelight`) and turns the TV off via `media_player.turn_off`."*

**Corrected 2026-10-10 (live-verified): the claim that `light.plug_green_tablelight` is "the one
thing `headboard-kill-all` does not cover" is wrong.** The live `headboard-kill-all` config lists
`light.plug_green_tablelight` ("Glass Table Light") in its `light.turn_off` target list, and a
repo-wide `ha_search("plug_green_tablelight")` returns exactly **one** config match — `headboard_kill_all`
itself (0 entities, 0 scripts, 0 scenes, 0 helpers, 0 dashboards). So the Glass Table Light is
already in the bedtime kill list and the open question this section used to flag is **closed**:
nothing needs adding anywhere.

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
| `bedroom-sleep-now` (deleted 2026-10-10) | n/a — absorbed into `headboard-kill-all`, which turns these outlets off |

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
| Battery-low alerts for the contacts | **not built** | The `*_battery_low` entities exist and are `off`; one quiet notifier is better than four. Pairs naturally with the front-door lock battery alert. Plan item, no urgency on fresh batteries |

## Planned (not yet built)

- **Front door (Entry)** → `binary_sensor.front_door`. The quiet set: *ajar while `lock.termite_towers` reports `locked`* (a U-Bolt has **no door-position sensor** and is a **SmartThings cloud** device, so "locked but not latched" is invisible today) → notify + `camera.front_door_live_view` snapshot; *opens 23:00–06:00 with `anyone_home` off* → notify + Ring snapshot; *same window with someone home* → **`logbook.log` only, zero notifications**; plus patching `door_layer_cross_check` to use a local sensor instead of two cloud ones.
- **Deck door (upper deck, off the bedroom)** → quiet announce after 30 min open with the bedroom empty. A single contact cannot distinguish "winter cooling by design" from "left open" — that needs the **main + screen pair**.
- **PIR #1 → 2nd Hallway**, **PIR #2 → Master Bath**.
- **`button-bedhead-steve`** → added as an extra trigger to the existing `badtime.tv` and `headboard-kill-all` (today the entire bed-gesture system is `button-bedhead-matt` only). `bedroom.sleep.now` is deliberately **not** in that list: it is superseded by `headboard-kill-all` (which absorbed its config, including the Glass Table Light), shared its exact single-press trigger, and **has since been deleted** — there is nothing left to add (see "Superseded" above).
- **A generic `doors-open-while-away`** across all contacts, `for: 2 min`.

## House facts that shaped the plan

- **Catio = fenced-in back yard** (the cat patio); **Cattic = the attic**, another cat play room.
- The catio is **two floors**: lower deck off the **Laundry** (the "main catio door"), upper deck off the **master bedroom**. The cats can nudge the main door open if it is not latched. A **shelf beside it opens the cat door**, so in winter the main door can stay shut.
- **Only the sauna door can block the cats.** Both Green Room sliding barn doors (to the 1st bath and to the laundry) have **cat cutouts**; the master bath door is never closed, and the basement door is hinged and left open for the cats and air circulation. The barn doors are closed only when it is cold. (The Sauna is separated from the Green Room by a **wall** — its own door swings into the narrow 1st bath.)
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

- **The two Entry airlock leaves are unsensed.** The **Hallway door** (double
  hinged, two ~20 in leaves; `mwave_entry_*` sits on the Entry side) and the
  **Kitchen pocket door** (slides into the wall) both rest **closed** by the
  household airlock policy, so a contact on each would make the Entry a genuinely
  observable airlock. Today neither the front door nor either interior leaf is
  sensed ([house-layout.md](house-layout.md) §2.7).
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
- No battery-low alert exists for the four contacts or the U-Bolt lock.
- Windows remain HAL's largest blind spot: no alarm panel and no window contacts.
- `hams/inventory/` still holds a placeholder device file (example MACs), and the
  `snipeit` schema referenced by `hal-context.md` / `wiki/agent-index.md` **does
  not exist** in `ttdb`, so nothing machine-readable tracks spare hardware.

## Verification note — 2026-10-08 (read-only pass)

A read-only pass over the three deployed contacts and every automation that consumes them.
**Nothing was changed.** States, timestamps, traces and automation configs below were all
queried live through `hal-mcp` on 2026-10-08 (HA timezone `America/Toronto`). The file's CCM
header was refreshed at the end of the pass so its metadata matches the new content.

### The contacts are alive and reporting

| Entity | State | Last state change | Behaviour |
|---|---|---|---|
| `binary_sensor.bedroom_door` | `on` | 2026-10-08 07:58:21 | ~80 state changes in the 8-day window read here; normal open/close cycling plus long night-time `off` holds (6 h 19 m, 3 h 52 m, 3 h 41 m …) |
| `binary_sensor.catio_door` | `on` | 2026-10-08 19:36:30 | 99 transitions in the 10-day window |
| `binary_sensor.sauna_door` | `on` | 2026-10-07 08:21:12 | **zero** genuine transitions — expected, see below |

The `sauna_door` row is not a fault. The sauna contact is normally **open** (`on`), so the cat's
water-bowl access reads as "open" continuously; `sauna-door-cat-water-guard` has
`last_triggered: null` because it exists for the opposite event (door **closed** on the bowl).
Its `2026-10-07 08:21:12` timestamp is the Zigbee2MQTT/HA restart (`unavailable` 08:05:01 →
`unknown` 08:21:12 → `on`), not a door movement.

The automations that consume the contacts all ran today, which proves the chain end-to-end
(radio → contact → entity → automation):

| Automation | Last successful run |
|---|---|
| `bedroom-door-verified-shut` (arms the gate) | 2026-10-08 07:13:06 |
| `bedroom-door-opened-night` | 2026-10-08 00:07:02 |
| `bedroom-night-settled-reset` | 2026-10-08 12:00:00 |
| `catio-door-indicator` | 2026-10-08 19:36:30 |

### Open finding — `bedroom-door-closed-settle-in` has been blocked since 2026-09-30

The settle-in is the only automation that latches `input_boolean.bedroom_night_settled`, and the
morning step-up is gated on that latch. Its last successful run was **2026-09-30 21:55:43**; the
last successful `bedroom-door-opened-morning` was **2026-10-01 08:38:05**.

- **The trigger is healthy.** Every trace begins exactly 5 s after the door reports `off`
  (22:34:32, 00:07:13, 06:27:09, 07:11:11 …), and every one ends `failed_conditions` — so the
  door edge is arriving and something downstream is rejecting it.
- **The blocker is the room-lit condition.** In the detailed trace of the in-window run at
  **2026-10-07 22:34:32** (door `off` at 22:34:27, latch clear, `mwave_bedroom_presence` `on`),
  conditions 0–2 pass and **condition 3 fails**, resolved against the first entity in its list:

  | # | Condition | Entities | Result |
  |---|---|---|---|
  | 0 | time 21:00–05:30 | — | ✔ |
  | 1 | `input_boolean.bedroom_night_settled` is `off` | — | ✔ |
  | 2 | someone in the room | `binary_sensor.mwave_bedroom_presence` | ✔ |
  | 3 | room is lit | `light.panel_light`, `light.tl_bedroom_rgbcw_lightbulb2`, `light.bulb_bedroom_pole_lower`, `light.smart_light_23061297829567590a0148e1e9ca187f` | ✖ |

- **Three of the four listed lights were `on` at that moment** — `tl_bedroom_rgbcw_lightbulb2`,
  `bulb_bedroom_pole_lower` and the Tuya panel all switched on together at 22:32:39. The only
  dark one was **`light.panel_light`**, `off` continuously since 2026-10-07 14:37:06 with no
  transitions in the 30-hour window. HA's multi-entity `state` condition is a conjunction
  (demonstrated by exactly this trace: three of four matched and it still failed), so a single
  permanently-off lamp in that list vetoes the whole settle-in.
- **Knock-on.** With no latch set since 09-30, `bedroom-door-opened-morning` fails on
  **condition 1 (the latch)** — confirmed in its 2026-10-08 07:58:21 trace — so the dim-orange
  wake step has been dark since 2026-10-01. The bedtime scene/TV re-assert, the very-dim-red
  night path and the library-pole-off have likewise not been applied by this automation since
  2026-09-30.

Not fixed here, by design (read-only pass). Options for whoever picks it up: drop
`light.panel_light` from that condition, relax it to an any-of match (`match: any`, or an `or`
block), or fix whatever used to switch `panel_light` on. Worth deciding separately whether "room
lit" should be an illuminance or scene test rather than a hard-coded lamp list — note that the
night path this automation applies only ever turns on `bulb_secondfloor_stair_hallway`,
`bulb_masterbath_ceiling_light` and `tl_bedroom_rgbcw_lightbulb1`, **none** of which appear in
the condition's list.

### The windows printed in the choreography table above are stale

The 05:30 split was implemented, but the table under *"The gate and the reworked bedtime
choreography"* still prints the pre-split values. Live configs read during this pass:

| Automation | Window (live config) | Table says |
|---|---|---|
| `bedroom-door-opened-night` | 21:00 → **05:30** | 21:00 → 06:00 |
| `bedroom-door-closed-settle-in` | 21:00 → **05:30** | 21:00 → 06:00 |
| `bedroom-door-opened-morning` | **05:30** → 12:00 | 05:00 → 12:00 |

`bedroom_asleep` is a third, separate entity (`hour >= 21 or hour < 6`) — three entities, three
purposes, no conflict.

### Threads closed in this pass

- **"Nothing has fired since 2026-09-24."** The three automations retired in the rework are still
  present and switched **off** (`state: off`; registry `enabled: true`, re-verified 2026-10-10):
  `bedroom-night-exit-nightlight`, `bedroom-door-closed-arms-sleep`, `bedroom-wake-release`.
  Quietness there is the intended outcome.
- **No `linkquality` data.** All three entities exist but are registry-disabled by the
  integration: `sensor.0xa4c13881970be516_linkquality`,
  `sensor.0xa4c13849ae8c0a3a_linkquality` and `sensor.0xa4c138d17e20fd58_linkquality` each read
  `disabled_by: integration`, `enabled: false`. They therefore have no state and never appear in
  entity searches. Enable them if signal quality is wanted while commissioning the remaining
  devices.
- **Search caveat — RESOLVED 2026-10-10.** The one automation that was unreadable through
  `/config/automation/config` (404) was `automation.llm_hooktest_1`, and it was **not** a
  YAML-defined automation: it was a config-less *registry* orphan (the REST 404 came from having no
  body anywhere — there is no `automations.yaml` in the repo). It has been removed with
  `ha_remove_entity`, so the 404 is gone and automation-config searches no longer have a blind
  spot. See [hal-context.md](hal-context.md) §7.
- **This file's CCM header** says `%ccm_git_file_eol: CRLF` while the file is LF-only (zero CR
  bytes) — and refreshing the header does **not** correct it. The CCM EOL probe
  (`git-automation/v2/ccm-lib.sh`, and the same line in `update-ccm-header.sh`) tests
  `grep -q $'\r\n' "$file"`, whose pattern splits into CR plus an empty alternative; the empty
  alternative matches every line, so the probe reports **CRLF for any text file** — verified by
  running it against a file containing no CR byte at all, which still returned CRLF. Trust the
  bytes (`grep -c $'\r' <file>`), not the field. Left as-is here: shared hook tooling, not this
  document's business.

---

## Verification note — 2026-10-13 (write pass: cat door merged, lamp made single-writer)

This pass **changed** things (unlike the 2026-10-08 read-only pass above). All
state, configs, traces and hashes below were queried live through `hal-mcp`.
Timezone `America/Toronto`. Snapshot taken before the first write:
`ha_manage_backup(scope="snapshot", action="create", name="Before_catio_indicator_merge")`
→ backup id `e40b7273` (57.6 MB).

### 1. The ex-spare is now a live, named entity

| Was | Now |
|---|---|
| `binary_sensor.lower_cat_door_sensor_contact` (Z2M `lower.cat.door.sensor`, IEEE `0xa4c13890c8c6fe04`, `area_id: null`) | `binary_sensor.cat_door` (same device, area `catio`) |

Renamed with `ha_set_entity(new_entity_id=...)`; area set with
`ha_set_device(area_id="catio")`. The registry `unique_id`
(`0xa4c13890c8c6fe04_contact_zigbee2mqtt`) is unchanged, so a later Z2M rename
cannot break the entity id. **The name `binary_sensor.cat_door` was free**
(`ha_get_entity` → `Entity not found`) and does not collide with the existing
`binary_sensor.catio_door` — the two are deliberately distinct: **`catio_door` =
the human door off the Laundry; `cat_door` = the cat door behind the shelf.**

**Not done, deliberately:** the *device* name was left as `lower.cat.door.sensor`.
`Catio.door`, `Sauna.door` and `Bedroom.door` all have `name_by_user: null` with
`default_name` supplied by Z2M (`mqtt_topic_hint: zigbee2mqtt/Catio.door/...`),
i.e. **the `X.door` convention lives in Zigbee2MQTT, not in the HA registry**.
Setting an HA override would have been the wrong layer. Rename it in Z2M if
wanted.

### 2. `automation.catio_door_indicator` now carries the full precedence

Config hash `9ada523bfc500539` → **`d739d65f15966195`** (rewritten via
`python_transform`, so `id` `1790207238851` and `alias` were preserved).
`mode: single` → **`restart`**.

Triggers went 3 → **7**: both contacts (`catio_door`, `cat_door`) on **and** off,
`lock.termite_towers` `to: "unlocked"` **and** `from: "unlocked"`, plus the
`homeassistant` start recovery.

Actions are a two-branch `choose` with `default`:

| State | Colour | Brightness |
|---|---|---|
| front door **unlocked** | **red** `rgb 255,0,0` | **100 %** |
| either catio contact **open** | amber `rgb 255,40,0` | 40 % |
| all clear | green `rgb 58,255,47` | 36 % |

**Branch order is load-bearing.** Red is tested first and wins outright; amber's
`condition: or` covers the two contacts. The amber condition is written as an
explicit `or` of two `condition: state` nodes rather than one state condition
with `match: any` — with a bare entity list the state condition's `match`
**defaults to `all`**, which would have silently required *both* doors to be open
and left the single-open-door case green.

**Why red is @100 % and not @40 %:** the existing amber `rgb 255,40,0` is hue
9.4°, and pure red `rgb 255,0,0` is hue 0° — on an LED bulb those are practically
the same colour, so red-at-40 % would have been indistinguishable from amber and
the precedence would have been invisible. Differentiating by intensity (100 % vs
40 %) keeps amber and green byte-identical to their previous values while making
red unmistakable. If red at full brightness is too loud, the single number to
change is the red branch's `brightness_pct`.

**Fail-quiet by construction.** Every lock test is the literal `"unlocked"`;
nothing keys on `unavailable` or `unknown`. A lock that blips to `unavailable`
(the nightly ~0.3 s blip this lock logs) therefore degrades to amber/green rather
than latching red. A security-purist might prefer the opposite; that is an open
decision, not an oversight.

**The write was a live no-op, as intended.** With `lock=locked`, `catio_door=on`
and `cat_door=on` the new config resolves to amber — and the lamp was already
amber. Post-write the lamp read `on` / brightness `102` / `rgb [255,44,2]` with
`last_changed` still `19:20:00`, i.e. **no visible change and no spurious
transition.**

### 3. `automation.glucose_over_7` — deleted

Deleted at owner direction (`ha_config_remove_automation` → `result: ok`,
`unique_id 1775864309612`); `ha_get_state` now returns `Entity not found`. It was
deleted rather than disabled because it was **already dead**: `state: off`,
`last_triggered: 2026-04-10`, **zero** logbook entries in the preceding 168 h, and
its trigger referenced **`sensor.matthew_pegg_glucose_level`, which does not
exist** (the real entity is `sensor.matthew_pegg_glucose_level_2`). The high-
glucose alert had therefore been silently broken for months, and the automation's
only remaining live capability was a latent device-targeted write to the lamp.

Verbatim config, for anyone rebuilding it as a notification instead:

```json
{"id": "1775864309612", "alias": "glucose over 7", "description": "",
 "triggers": [{"trigger": "numeric_state", "entity_id": ["sensor.matthew_pegg_glucose_level"], "above": 7}],
 "conditions": [],
 "actions": [{"device_id": "1271c800e7c03abe59660ffcf3b81b1e", "domain": "light",
              "entity_id": "6e9bf1b641e64203293fc0cb0cbe47d6", "type": "flash"}],
 "mode": "single"}
```

Note the action was **device-targeted** (`device_id` plus the device's light
entity), which is exactly why a plain entity-id grep cannot be trusted to find
lamp writers — the audit below had to run twice, once by entity id and once by
device UUID.

### 4. Single-writer is now proven, not assumed

| Probe | Result |
|---|---|
| `ha_search("light.bulb_living_tablelamp")` over automations/scripts/scenes/helpers | **exactly 1** — `automation.catio_door_indicator` (`match_in_config: true`); scripts/scenes/helpers empty |
| `ha_search("1271c800e7c03abe59660ffcf3b81b1e")` (lamp **device** UUID) | **0** matches — glucose was the only device-targeted writer |
| `automation.glucose_over_7` | `ENTITY_NOT_FOUND` |

`light.bulb_living_tablelamp` now has **one** writer.

### 5. A reload does not fire the `homeassistant` start trigger

Counter-intuitive but worth recording: writing the automation config reloaded it
(proved by the `mode: restart` attribute appearing on
`automation.catio_door_indicator` and its `last_changed` moving to `20:33:41`),
yet **`last_triggered` did not move** and no `Home Assistant starting` trace was
created. The `start` trigger fires on a genuine HA start — the
`23:19:59 UTC "Home Assistant starting"` trace from the Z2M/HA restart is the
proof — but **not** on an automations reload. Consequence: between a reload and
the next door/lock transition the lamp colour is not re-asserted. This is
pre-existing behaviour (the old 3-trigger config had the same recovery trigger and
the same property), not a regression.

### 6. Open items from this pass

- **Cat-door polarity is unverified** (see the polarity section above) — the
  decisive test is **closing** the door and watching it flip. A static read while it
  is open cannot discriminate, because the door is open by default. Until then the
  cat door's amber state rests on an assumption. If it does test inverted, the fix
  is **physical** (rotate the magnet) — `automation.catio_door_indicator` is not to be
  edited, per the decision below.
- **Amber semantics for the cat door — decided 2026-10-13: keep as written.** The
  door is open by day by design, so `amber = cat_door open` holds the lamp amber
  through most daytime hours and starves the green "all clear" state. Considered and
  rejected: dropping `cat_door` from the amber `or`, ambering on the *anomalous*
  state instead, and gating to night-time hours. The owner accepted amber-most-of-
  the-day, so **no config change is planned** — including **no** swap to
  `state: "off"` should the polarity test come back inverted; fix that at the magnet.
- **`binary_sensor.catio_door` has `area_id: null`.** Its new sibling is now in
  `catio`; the older contact was never assigned one. Left alone as out of scope.
- **The cat-door contact has no `unavailable` handling** in the indicator: an
  unreachable cat-door contact falls through to green, which is the *quiet*
  direction for a cat-access signal. The catio door behaves the same way. If
  either should fail *loud*, that is a design decision to make deliberately.
- **`sensor.0xa4c13890c8c6fe04_linkquality` is registry-disabled by the
  integration** (same shape as the three older contacts) — enable it if signal
  quality is wanted while commissioning (step 5 of the procedure above).
- **`automation.catio_door_open_when_away` still watches only
  `binary_sensor.catio_door`**, not the new cat door. Deliberate for now: the cat
  door is a cat route, and texting on it would trip the "no panic" rule.

---

## Verification note — 2026-10-13 21:09 (cat-door polarity re-check, HAL back up)

Read-only: HAL was reachable again and **nothing was written to HA**. This pass
**corrects a factual error** in *Polarity — verify, don't assume* above, records
the cat-door history in full, and leaves the decisive test outstanding.

### The cat door has still never been seen to close

Full recorder history for `binary_sensor.cat_door` since it was paired — 11 rows,
all 2026-10-13, `America/Toronto`:

| Time (EDT) | State | Cause |
|---|---|---|
| 17:11:11 | `unavailable` → `unknown` | pairing — the entity appears |
| **19:07:19** | **`on`** | **first real contact reading** |
| 19:19:32 → 19:19:35 → 19:20:35 | `unavailable` → `unknown` → `on` | HA restart (`Home Assistant starting` trace 19:19:59) |
| 20:32:58 | `on` (re-report) | no state change |
| 20:41:52 → 21:02:09 | `unavailable` (twice) | HA down ~21 min, restarted 21:03:07 |
| 21:03:20 → 21:03:21 | `unknown` → `on` | HA restart (`Home Assistant starting` trace 21:03:07) |

**There is no `off` row anywhere in the history.** Every non-availability row is
`on`. Two consequences:

1. **The earlier note's "one real reading (`on`, at 17:11:11)" was wrong.**
   17:11:11 is the *pairing* row (`unavailable`→`unknown`); the first `on` is
   19:07:19. The error conflated the phantom availability rows with a contact
   reading.
2. **The churn is not door movement.** Every `unavailable`/`unknown` row tracks an
   HA restart or the Z2M/HA outage, never the flap. The `unknown`→`on` restore is
   the retained Zigbee state being republished: it looks like a transition and it
   *does* fire the automation's `to: "on"` trigger, but it is not one.

### What this settles, and what it does not

- **The `off` = closed mapping is real and reachable on this install.** The sibling
  `binary_sensor.catio_door` is the **same model, same Zigbee2MQTT flow, same
  `device_class: door`**, and its history proves the mapping end-to-end: `off` held
  from 2026-10-12 22:00:23 to 2026-10-13 06:54:55 (**8 h 54 m** overnight while the
  human door was shut), then `on` at 06:54:55. So this contact family here does
  report `off` = closed, and the Z2M→HA inversion layer is not a suspect. Caveat
  worth stating plainly: that proves the *composite* is right for the catio door; it
  cannot prove the cat door's own magnet is mounted the same way.
- **Not settled — the cat-door polarity itself.** The flap has still never been shut
  while the recorder was watching, so no `off` row exists. `on` = open remains
  inherited from `device_class: door`, not observed. The remaining unknown is
  narrowed to exactly one thing: **whether the cat-door magnet is positioned so the
  flap's shut position brings it into the reed's range** — the same class of fault
  the bedroom contact had before its 2026-09-24 magnet move.
- **Availability churn is a blind spot for the test.** A close landing inside any of
  the windows above would be swallowed. Do the test while the entity reads `on` and
  Zigbee2MQTT is up.

### The decisive step is unchanged

**Close the flap and re-read.** `off` on close ⇒ `on` = open, leave everything
alone. Still `on` while the flap is physically shut ⇒ closed reads `on`, and the fix
is the **magnet**, not the automation — the amber decision below stands either way
and `automation.catio_door_indicator` is not to be edited.

### The automation is untouched, and the decision is intact

- `ha_config_get_automation("automation.catio_door_indicator")` → `config_hash`
  **`d739d65f15966195`**, byte-identical to the write pass. No edit has occurred
  since, and none is planned.
- `mode: restart`; `last_triggered` **2026-10-13 21:03:21.131**, fired by
  *state of `binary_sensor.cat_door`* (trace `ce55c3f2…`) — the restore path fired
  the `to: "on"` trigger, so a restart **does** re-assert the lamp.
- Live lamp: `on`, brightness **102** (40 %), `rgb_color [255,44,2]` — the amber
  branch, exactly as designed. The bulb reports `[255,44,2]` rather than the
  configured `[255,40,0]` because it runs in `xy` colour mode (it read `[255,44,2]`
  in the write pass too, so this is not drift).
- The accepted tradeoff is therefore observable in production right now: with
  `cat_door` `on`, the lamp sits amber and the green "all clear" state is suppressed.

### Two genuine restarts confirm the §5 reload/restart split

The write pass recorded that a *reload* does **not** fire the `homeassistant` start
trigger. Two real restarts since confirm the other half — `Home Assistant starting`
traces at **19:19:59** and **21:03:07**. Restarts re-assert; reloads do not.

---

## Update — 2026-10-14 19:14 (magnet adjusted; the contact finally reports `off`)

Read-only. The 21:09 note above left the close-transition test outstanding. Overnight
the magnet was **physically adjusted** — the fix the decision below prescribes — and
the contact now behaves very differently.

- **`binary_sensor.cat_door` now produces `off`**, which it had never once done
  before this: **85 state rows in 30 h**, versus 11 rows in its entire prior life.
- The adjustment session is legible in the data: **six `off`→`on` pairs between
  21:10:15 and 21:12:40** on 2026-10-13 (2 min 25 s) — someone working the magnet,
  not a cat.
- **Best polarity correlation available.** After the working stopped, the contact
  settled into a **9 h 25 m `on` hold** overnight (2026-10-13 21:12:40 →
  2026-10-14 06:45:31) and later a **3 h 47 m `off` hold** (2026-10-14 08:11:00 →
  11:58:09). That matches the flap being left **up** all night and **down** through
  the morning — i.e. **`off` = closed, `on` = open**, the standard mapping. The
  magnet fix appears to have worked.
- **New physical finding — the gap looks marginal.** Most of the 85 rows are **rapid
  off/on pairs** 0.2–4.5 s apart (08:05:57→08:06:02, 08:09:15→08:09:15,
  08:09:32→08:09:34, 08:09:47→08:10:07, 08:10:08→08:10:10, 11:58:10→11:58:11 …).
  That chattering is the same signature the **bedroom** contact showed *before* its
  2026-09-24 magnet move: the reed sits at the edge of the magnet's range, so the
  closed position does not hold cleanly. Worth confirming the flap's *resting* closed
  position holds `off` for >60 s with no chatter — if not, the bedroom remedy
  applies (a spacer behind the magnet).
- **Behavioural, not electrical.** The flap is left in whatever position it was last
  put: up all night here, down through the morning. The contact faithfully reports
  that — which is precisely why a single read can never settle polarity for an
  open-by-default door, and why the "closed ⇒ `off`" correlation above needed a
  sustained hold to become visible at all.
- **A chattering contact spams the indicator.** `automation.catio_door_indicator`
  triggers on every edge, so 85 rows in 30 h is 85+ extra automation runs. Its
  `mode: restart` absorbs that without interleaving, but the lamp is being re-asserted
  far more than the door actually moves. Fixing the gap also quiets the automation.

**No automation was edited.** `automation.catio_door_indicator` still reads
`config_hash d739d65f15966195` — unchanged since the write pass, as the decision
requires.

---

## Update — 2026-10-14 19:17 (second indicator lamp: Mister P, red / yellow / green)

Owner request: a second lamp should render the catio-access state, with the
door-open colour **time-boxed to darkness**. This pass **wrote** to HA (snapshot
`7ff66b42`, 58.8 MB, taken first).

### Why the lamp "did not change colour": nothing drove it

`light.mister_p_rgbcw_lightbulb` (Tuya local, Living Room, `hs` + `color_temp`,
device `14d460dd14819823b900eeede4c376ea`) had **zero writers**. Audited before
writing: `mister_p` → **0** matches and the full entity id
`light.mister_p_rgbcw_lightbulb` → **0** matches, across
automations/scripts/scenes/helpers/dashboards. It was sitting `on`, blue, from a
manual 21:42 change.

### `automation.mister_p_door_indicator`

`unique_id 1792019846390`, `config_hash 79cdd28785c4b0d6`, `mode: restart`.

| State | Colour | Brightness |
|---|---|---|
| front door `lock.termite_towers` **unlocked** | **red** `rgb 255,0,0` | 100 % |
| a catio-access contact open **and dark** | **yellow** `rgb 255,200,0` | 60 % |
| otherwise | green `rgb 58,255,47` | 36 % |

Nine triggers: four catio-contact edges (`catio_door`, `cat_door` × on/off), two
lock edges, `sun` **`sunset`**, `sun` **`sunrise`**, and the `homeassistant` start
recovery.

### Deliberate decisions worth preserving

- **Scope is the catio pair only** (`catio_door` + `cat_door`), chosen by the owner
  over all four contacts. The bedroom and sauna doors are not part of this lamp.
- **"Front door open" has no contact to key on.** The front door is **Ring-only**
  (`event.front_door_ding`, `event.front_door_motion`,
  `sensor.front_door_last_activity`, `camera.front_door_live_view`,
  `sensor.front_door_battery` — and no `binary_sensor.front_door`). Red therefore
  keys on `lock.termite_towers` ≠ `locked`, the same signal the table lamp's red
  uses. If a real open/closed signal is ever wanted, it needs new hardware.
- **Yellow is deliberately narrow: a catio door open during daylight reads GREEN.**
  Those doors are open *by design* all day, so a daytime open door is not an alert
  condition. Green here means "no action required", not literally "everything is
  shut". **Do not "fix" this by un-gating yellow** — that recreates the
  amber-all-day problem the table lamp accepted, and the time box was an explicit
  owner request.
- **The sun triggers are load-bearing, and the boundary is `sunset`/`sunrise`, not
  `dusk`.** The owner said "after dusk … before sunrise", but **HA's sun trigger
  accepts only `sunset` or `sunrise`** — submitting `event: dusk` is rejected with
  *"expected 'sunset' or 'sunrise' at 'options.event'"*. There is no native `dusk`
  trigger, so the `condition: sun` was aligned to `after: sunset` /
  `before: sunrise`, keeping the trigger and the condition on **identical** edges.
  Had the condition kept `after: dusk`, the lamp would stay green from sunset until
  some *unrelated* event fired after dusk. Cost: yellow onset is ~30 min earlier than
  true dusk (from `sun.sun`: `next_setting` 22:33:40Z vs `next_dusk` 23:03:06Z, i.e.
  18:33 vs 19:03 EDT).
- **The table lamp is untouched.** `automation.catio_door_indicator` keeps its
  red/**amber**/green scheme at `config_hash d739d65f15966195`; the two lamps
  intentionally use different middle colours (amber `255,40,0` vs yellow
  `255,200,0`).

### Verified live, not assumed

The automation was fired with `automation.trigger` at **2026-10-14 19:17:32 EDT**
(trace `0069b66ca967c9f9a33d1e222f88dbb3`). At that instant `lock.termite_towers`
was `locked`, `catio_door` `off`, `cat_door` `on`, and the sun was inside the
sunset→sunrise window — so the correct answer was **yellow**, and the lamp went to
`on` / `rgb_color [255,200,0]` / `hs_color [47,100]` / brightness `153` (=60 %).
That one observation proves the red branch was skipped **and** that both conditions
of the yellow branch — the `sun` window *and* the contact `or` — evaluated true.

Note the lamp's `last_changed` did **not** move (still `2026-10-13T21:02:07`) because
only attributes changed; `last_reported` moved to 19:17:32. That is the same
phenomenon recorded for the table lamp in the write pass — an attribute-only change
does not move `last_changed`.

### Still unverified

- The **red** branch — would require unlocking the front door; not done remotely.
- The **green** branch's daytime case — needs a daytime sun; the `sunrise` trigger
  will exercise it. Both are literal-value / `default` paths with no templates, so
  they fail loudly rather than silently.
- Mister P is now a **second** lamp whose colour is claimed by an automation. If it
  is ever wanted as a plain decorative lamp again, this automation is the thing to
  disable — it will otherwise override any manual colour on the next door, lock or
  sun event.

