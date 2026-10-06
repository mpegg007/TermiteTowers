<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: hams/docs/house-layout.md:174 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: 11d076154d012021b44cdf6bef1728b8b2ed96b5 % -->
<!-- %ccm_git_commit_id: da4a17aa441e345b23a66ad8ed67773c5edcd740 % -->
<!-- %ccm_git_commit_count: 174 % -->
<!-- %ccm_git_commit_date: 2026-10-06 19:11:37 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: vacuum maps + house layout: stair geometry refined (two-run switchback, 2 ft second-floor offset) % -->
<!-- %ccm_git_modify_date: 2026-10-06 19:11:37 % -->
<!-- %ccm_git_file_last_modified: 2026-10-06 19:11:05 % -->
<!-- %ccm_git_file_name: house-layout.md % -->
<!-- %ccm_git_path: hams/docs/house-layout.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: utf-8 % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 31322 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
 <!-- %git_commit_history: 2026-10-06 mpegg  vacuum maps doc + house-layout vertical structure  --> 
 <!-- %git_commit_history: 2026-10-05 mpegg  house layout + routines docs  --> 
 <!-- %git_commit_history: 2026-10-05 mpegg  house layout + routines docs  --> 
# House Layout — rooms, floors, sensors, and blind spots

> **What this is:** the physical model of the house — which rooms exist, which
> floor they sit on, which sensor watches each one, and — just as important —
> which rooms have **no** sensor at all. This is the file to read before writing
> any automation that reasons about *where someone is*.
>
> **What this is NOT:** an authority for any live value. Entity IDs drift, sensors
> get renamed/re-batteried, areas get re-parented. Always confirm IDs and states
> live via the `hal-mcp` tools. See [hal-context.md](hal-context.md) §8.
>
> **Companion files:** [routines.md](routines.md) (who does what, when) ·
> [hal-context.md](hal-context.md) (instance snapshot) ·
> [zigbee-door-sensor-rollout.md](zigbee-door-sensor-rollout.md) (contact plan) ·
> [vacuum-maps.md](vacuum-maps.md) (the robot vacuums' own floor plans vs this model).

- **Created:** 2026-10-04, from a user interview + live registry reads.
- **Sources:** `ha_list_floors_areas`, `ha_search` (entity registries), `ha_get_device`.
- **Status:** topology + sensor coverage are verified live. Route/cat notes marked
  *(user-provided)* are the owner's description, not sensor-derived.
- **How to read it:** §1 registry → §2 physical adjacency → §3 climate → §4 presence
  → §5 contacts → §6 naming traps → §7 route notes → §8 worked example →
  §9 maintenance.

---

## 1. Floors and areas

5 floors, 18 areas. HA's `level` numbering is **not** the colloquial one — the
Ground floor is `level: 1`, not 0.

| Floor | HA `level` | Area IDs (HA registry names) |
|---|---|---|
| **Basement** | `-1` | `basement` |
| **Utility** | *(null)* | `utility` |
| **Ground** | `1` | `entry`, `kitchen`, `living_room`, `hallway`, `hobby_room` (**Green Room**), `laundry`, `bathroom` (**1st Bath**), `workout` (**Backroom**), `sauna`, `catio` |
| **Second** | `2` | `bedroom`, `library`, `master_bath`, `office`, `2nd_hallway` |
| **Attic** | `3` | `cattic` |

Two names differ from their IDs — use the ID in automations, the name in prose:

- `hobby_room` → displayed as **Green Room**
- `workout` → displayed as **Backroom**

**Utility** (`level: null`) is a catch-all area, not a physical floor — it collects
entities that never got a real room assignment. Do not treat it as a location.

---

## 2. Physical layout & adjacency

§1 is the **registry** model — HA floors, areas, and the entities wired to them.
This section is the **building** model — how the rooms physically connect, where
the stairs and doors are, and where the two models disagree. Use §1 to pick an
`area_id`; use this section to reason about *movement*.

*(Everything below is user-provided unless marked verified. The sensor-visible
corollaries live in §4 (presence coverage) and §5 (doors and contacts).)*

### 2.1 Registry model vs physical model

The area registry is **flat**. An area carries only an optional `floor_id`, and a
floor is just a label carrying a `level`. Nothing records that Ground sits under
Second, and nothing records which areas share a wall. Two consequences bite any
location-aware automation:

- **`utility` is not a physical place.** Its `level` is `null` and it is a
  catch-all for entities that never got a real room assigned (see §1). Never treat
  Utility as a storey, or as a room a person can be "in".
- **One area ≠ one space.** `catio` is a single area at `level: 1`, but the Catio
  is physically **two decks on two different storeys** (§2.8). The registry cannot
  express that — so any "same floor" or "one room" inference keyed on the `catio`
  area is wrong.

### 2.2 Levels and vertical circulation

| Transition | Route | Sensor-visible? |
|---|---|---|
| Ground ⇄ Second | **switchback staircase** (~8 ft, U-turn, ~2 ft — see note) | **no** — no sensor on the stairs or in either Hallway |
| Second ⇄ Attic (Cattic) | **through the Office** | only at the Office end |
| Ground ⇄ Basement | internal stair — opens off the **Hallway / Green Room** end; **hinged door, normally open** (§2.5) | **no** |

Every floor change is therefore **invisible** to the sensor set: it must be
*inferred* from the pair of room sensors either side of the transition, and that
inference is unreliable (§4.2). The Zigbee coordinator lives in the **Office**.

**Stair share *(user-provided, geometry refined 2026-10-06)*:** the Ground ⇄ Second
staircase is a **switchback (U-turn) stair in two runs** — it rises **~8 ft, turns,
then climbs a final ~2 ft (~10 ft total)**. The **~80 % / 20 %** figure is that split
of the **rise** — the **long lower (~8 ft) run is the ~80 %**, the **short top
(~2 ft) run the ~20 %** — and because the **main Second floor sits ~2 ft above the
part over the Green Room** (§2.9), the same 80 / 20 also reads as the **Second
floor's own area split** (main part ≈ 80 %, over-Green-Room part ≈ 20 %). By the
owner's framing the **Second floor (its *main part*) holds the ~80 %** share of the
flight and the **Ground floor the ~20 %**, so **neither** robot vacuum's map holds the
whole staircase ([vacuum-maps.md](vacuum-maps.md) §3.3, §5, §6). Here **"the Second
floor"** is its **main part** — `bedroom`, `office`, `library`, `2nd_hallway` — i.e.
everything **except** the `master_bath`, which is the storey's lower part over the
Green Room (§2.4, §2.9).

### 2.3 Ground floor (level 1)

Confirmed physical connections:

| Connection | Door / opening | Contact |
|---|---|---|
| Green Room ⇄ Bathroom (1st) | sliding **barn door** (cat cutout) | none |
| Green Room ⇄ Laundry | sliding **barn door** (cat cutout) | none |
| Bathroom (1st) ⇄ Sauna | **sauna door** — swings into the narrow 1st Bath (§2.7) | `binary_sensor.sauna_door` |
| Bathroom (1st) ⇄ Backroom | **open** — no door, a clear sightline | none |
| Laundry ⇄ Catio (lower deck) | **main Catio door** | `binary_sensor.catio_door` |
| Entry ⇄ Kitchen | **pocket door** — slides into the wall; rests **closed** (§2.7) | none |
| Entry ⇄ Hallway | **double hinged door** — two ~20 in leaves; rests **closed** (§2.7) | none |
| Kitchen ⇄ Living Room | **open** — no door; a countertop on the east wall is the only divider | none |
| Entry ⇄ outside | front door | **none** — Ring camera only (§5) |

The **two** Green Room barn doors have **cat cutouts**, so they do not restrict
the cats and are closed only when it is cold. The **Kitchen** holds the fridge
(`binary_sensor.refrigerator_door`).

**A wall separates the Sauna from the Green Room** *(user-provided)* — there is
**no** direct Sauna ⇄ Green Room opening. The Sauna is entered only through the
narrow **1st Bath** (via its barn door), and from that bath the **Backroom**
(exercise room) is in sight.

**The front half of the Ground floor is one open room.** Entering from the
**Entry** through the pocket door (§2.7) puts you in a single large space that
holds the **Kitchen at the front of the house** and the **Living Room** behind
it. The *only* thing dividing them is a **countertop attached to the east wall**
— not a wall, not a door. So `kitchen` ⇄ `living_room` is an **open link**: the
two cannot be closed off from each other, and moving between them never crosses a
doorway.

From the Kitchen the sightlines run to the **Hallway**, the **Green Room** and
the **staircase to the Second floor**. The **basement stair opens from the
Hallway / Green Room end** (§2.5).

**"Galley" = the Kitchen.** *(user-provided: the kitchen, "counters on both
sides")* — the household's word for the Kitchen run. It is a synonym, not a
separate space: use `kitchen` / "Kitchen" in automations and prose.

> **Robot side (L40).** The **DreameBot L40** maps this Ground floor and segments it
> into 11 rooms that mostly agree with the above — but it splits the open
> Kitchen/Living Room into two, adds `Stairs`, and does **not** segment `entry` or
> `laundry`. Room-by-room reconciliation, saved map PNGs, and the two placeholder
> fragments (`Room 5` / `Room 11`) are in [vacuum-maps.md](vacuum-maps.md) (§3–§4).

### 2.4 Second floor (level 2)

Confirmed physical connections:

| Connection | Door / opening | Contact |
|---|---|---|
| Bedroom ⇄ 2nd Hallway | **interior** bedroom door | `binary_sensor.bedroom_door` |
| Bedroom ⇄ Catio (upper deck) | **deck door** — open by design in winter, screen leaf closed | `binary_sensor.deck_door` *(not yet paired)* |
| Office ⇄ Cattic (attic) | attic access **through the Office** | none (§4.2) |

The Bedroom has **two** openings — the interior door and the upper-deck door. The
sleep model keys on the **interior** door only; winter cooling keeps the deck door
open *by design*.

The Second floor is **not a uniform storey**: its **lower part is the Master
Bath**, which sits directly over the Ground-floor **Green Room** (§2.9) — the **same
size, stacked exactly**, so the Master Bath floor lands **~2 ft below** the rest of the
storey. Its **main part** — `bedroom`, `office`, `library`, `2nd_hallway`, i.e.
everything *except* the Master Bath — is the **~2 ft-higher level** the switchback
stair's short top run climbs onto (§2.2), is what **"the Second floor"** means in the
**stair-share** note, and holds the **~80 %** share of the storey's area and of the
Ground ⇄ Second flight.

### 2.5 Basement, sauna, and the non-room spaces

- **Basement** (`level: -1`) is **L-shaped — ~18 × 40 ft with a 6 × 12 ft corner
  missing, heavily obstructed**. The boiler lives down here
  (`sensor.esp32_boiler_*`). One PIR plus one mmWave is not enough coverage; the
  plan is 3 mmWave zones + a PIR at the entry.
- **Sauna** has **no light and no switch** — its only signals are the door contact
  (`binary_sensor.sauna_door`) and the `sauna-temp` probe. Its door **swings into
  the narrow 1st Bath**, and a **wall separates the Sauna from the Green Room**
  *(user-provided)* — so the 1st Bath is the only way in (§2.3, §2.7). Of the
  doors on the cat route it is the one that **can block the cats**: the Green Room
  barn doors have cutouts, the basement door is normally open, the Master Bath is
  never closed. It is normally left **open** so the cats can reach the water bowl
  — `automation.sauna_door_cat_water_guard` alarms on *closed* for 20 min
  ([zigbee-door-sensor-rollout.md](zigbee-door-sensor-rollout.md)).

The **basement stair opens from the Hallway / Green Room end** of the Ground
floor *(user-provided)*. Its door is **hinged** and **normally left open** — for
the cats and for air circulation *(user-provided)* — so at rest the basement run
is open and blocks nothing, and it stays **unsensed** (§2.2).

### 2.6 Canonical room names (prose ↔ `area_id`)

Use the **`area_id`** in automations and the **displayed name** in prose:

| Household name | HA `area_id` | Floor |
|---|---|---|
| Basement | `basement` | -1 |
| Utility | `utility` | *(null — not a floor, §2.1)* |
| Porch *(exterior)* | *(no area — not registered)* | *(outside)* |
| Entry | `entry` | 1 |
| Kitchen | `kitchen` | 1 |
| Living Room | `living_room` | 1 |
| Hallway | `hallway` | 1 |
| **Green Room** | `hobby_room` | 1 |
| Laundry | `laundry` | 1 |
| **1st Bath** | `bathroom` | 1 |
| **Backroom** | `workout` | 1 |
| Sauna | `sauna` | 1 |
| Catio | `catio` | 1 *(but two decks — §2.8)* |
| Bedroom | `bedroom` | 2 |
| Library | `library` | 2 |
| Master Bath | `master_bath` | 2 |
| Office | `office` | 2 |
| 2nd Hallway | `2nd_hallway` | 2 |
| Cattic | `cattic` | 3 |

**Household aliases (not `area_id`s):** *galley* = Kitchen (§2.3) · *Green Room*
= `hobby_room` · *Backroom* / *exercise room* = `workout` · *1st Bath* =
`bathroom`.

**Porch — an exterior space with no area.** What the household calls the *"porch"*
is the **gated ~20 ft frontage** at the front of the house: there is **no front
yard**, the sidewalk runs directly along the frontage, and a **gate** closes off
the narrow strip. It is an exterior space, not a room. *(Verified live: no `porch`
entity or area exists in HA, and there is no contact on the gate.)* The
back-of-house counterpart is the Catio (§2.8).

**No garage, no driveway.** *(user-provided)* The **gate, the frontage and the
front door are the only ingress/egress** to the property, so the Porch strip is
the whole of the front-of-house outdoor space — there is nothing else to name or
to give an area. *(Verified live: no `garage` entity or area exists in HA.)*

### 2.7 Doors and openings — the full physical set

§5 lists the contacts the *system* can see. This is the physical inventory,
including the openings with no contact at all:

| Opening | Between | Contact |
|---|---|---|
| Front door | Entry ↔ outside | **none** — Ring motion/ding + camera only |
| Pocket door | Entry ↔ Kitchen | none — slides into the wall; rests **closed** |
| Hallway door | Entry ↔ Hallway | none — **double hinged** (two ~20 in leaves); `mwave_entry_*` on the Entry side |
| Bedroom interior door | Bedroom ↔ 2nd Hallway | `binary_sensor.bedroom_door` |
| Deck door | Bedroom ↔ Catio upper deck | `binary_sensor.deck_door` *(pending)* |
| Main Catio door | Laundry ↔ Catio lower deck | `binary_sensor.catio_door` |
| Sauna door | Sauna ↔ Bathroom (1st, narrow) | `binary_sensor.sauna_door` |
| Green Room barn doors (×2) | Green Room ↔ Bathroom (1st) · Laundry | none — cat cutouts |
| Refrigerator door | Kitchen appliance | `binary_sensor.refrigerator_door` |

The **pocket door** sits between the **Entry and the Kitchen** and **slides into
the wall** — unlike the Green Room's **single-panel barn slider**, which stays
visible on its rail when open. *(Verified live: the `entry` area contains **no
contact sensor** — only `mwave_entry_*`, the Ring front-door camera/events, and
the door lock — so neither the pocket door nor the Entry ⇄ Hallway door is sensed
today.)*

> ⚠ **Still open:** whether either airlock leaf (**pocket door**, **Hallway
> door**) should get a **contact sensor** — both are unsensed today and the
> `entry` area holds no contact at all (§5). Their **resting state is settled** —
> see the airlock policy below.

**"Airlock" = the Entry.** The household term for the **Entry vestibule** — the
one space with a leaf to **outside the property**. (The Catio is also outdoors but
fully enclosed, so it does not count.) Its three leaves:

- **front door** → outside — Ring camera + ding, **no contact**
- **pocket door** → Kitchen — slides into the wall; rests **closed**
- **Hallway door** → Hallway — **double hinged**, two ~20 in leaves; rests
  **closed**; `mwave_entry_*` sees the Entry side

So a person entering or leaving always crosses the airlock, and the configuration
that matters is **which of the two interior leaves is open when the exterior one
opens** — today the system can see neither.

**Resting states — the airlock policy.** Both interior leaves rest **closed**
*(user-provided)*: the household keeps the **Hallway door** and the **Kitchen
pocket door** shut alongside the **front door**, so the Entry is a closed box at
rest. The **basement door** is the opposite — **hinged and normally open** for the
cats and air circulation (§2.5). The Green Room barn doors close only when it is
cold; the Master Bath is never closed.

**The sauna door opens into the narrow 1st Bath** *(user-provided)*, with the
**Backroom** (exercise room) in sight beyond it; a **wall separates the Sauna
from the Green Room**, so the 1st Bath is the sauna's only approach (§2.3). Its
contact is live (`binary_sensor.sauna_door`), and it is the interior door that can
**block the cats** (§2.5).

### 2.8 The cat spaces: Cattic and Catio

Two cat spaces, two very different models:

- **Cattic = the entire walkable attic.** HA models it as the single `cattic` area
  (`level: 3`) — one open top-floor cat play room. It has **no sensor**, and the
  only approach the system can see is **through the Office**, so an attic trip
  presents as an **Office** event (§4.2, §8). It spans **only the main part with
  the 10 ft ceilings** (Kitchen / Living Room) — there is **no attic over the
  Master Bath** — and its **front ~8 ft is too short to use** (§2.9).
- **Catio = a separate outdoor two-level deck** at the back of the house:
  - **Lower deck** — off the **Laundry**, through the **main Catio door**
    (`binary_sensor.catio_door`). The cats can nudge this door open if it is not
    latched; a **shelf beside it opens the cat door**, so in winter the main door
    can stay shut.
  - **Upper deck** — off the **Bedroom**, through the deck door. It is **open by
    design in winter** with the **screen leaf closed**. Physically it is the
    **flat roof over the Sauna / 1st Bath / Backroom / Laundry strip** (a plastic
    light panel over the Laundry) — see §2.9.

> **Registry wrinkle:** HA holds **one** `catio` area at `level: 1`, so the upper
> deck has **no area of its own**. "Cattic" only ever means the house attic;
> "Catio" only ever the outdoor deck. Full device + contact plan:
> [zigbee-door-sensor-rollout.md](zigbee-door-sensor-rollout.md).

### 2.9 Vertical structure — what sits over what

*(user-provided)* The house stacks **asymmetrically**, so the Second floor is not
a copy of the Ground floor and the roofline is not flat. This is the section to
read before reasoning about "above"/"below" between storeys.

- **Master Bath sits directly above the Green Room — *same size, stacked exactly*.** The
  `master_bath` footprint **is** the Green Room's (`hobby_room`) footprint, one storey
  up. Because the Green Room has an **8 ft ceiling** where the Kitchen / Living Room —
  the *main part* — have **10 ft**, the Master Bath lands **~2 ft lower** than the rest
  of the Second floor: it is the storey's **lower part** (§2.4). That ~2 ft step is
  exactly the **short top run of the Ground ⇄ Second switchback stair** (§2.2) — the
  stair rises **~8 ft, U-turns, then climbs the final ~2 ft** onto the main Second floor.
- **Flat roof over the back-eastern strip.** Above the **Sauna**, the **1st Bath**
  and the **Backroom** is a **flat roof**; above the **Laundry** that flat roof is
  **plastic — a light panel**. **All of that flat roof *is* the Catio's upper
  deck** (§2.8): the "upper deck" is literally the roof of the Sauna / 1st Bath /
  Backroom / Laundry strip.
- **The attic (Cattic) does not extend over the Master Bath.** It spans **only the
  main 10 ft-ceiling part** (Kitchen / Living Room), and its **front ~8 ft is too
  short to use** — a sloped-roof taper. The registry's `cattic` area (`level: 3`)
  therefore covers **less than the full footprint**: **no attic above the Master
  Bath**, and the rear roof strip belongs to the **Catio**, not the attic.

Reading this with §2.1 (the flat registry): "above"/"below" between areas is *not*
recoverable from HA — it is only in this table.

---

## 3. Climate coverage (temperature / humidity per area)

These are the entities the area registry points at, so they define "the room's
climate sensor". Rooms listed as *none* have **no** temp/humidity entity wired to
the area.

| Area | Climate entity prefix | Notes |
|---|---|---|
| Basement | `sensor.esp32_boiler_boiler_room_*` | boiler room; `mwave_basement_*` also present |
| Entry | `sensor.mwave_entry_*` | |
| Kitchen | `sensor.mwave_kitchen_*` | |
| Living Room | `sensor.mwave_living_tv_*` | |
| Bathroom (1st) | `sensor.mwave_1stbath_*` | |
| Bedroom | `sensor.esp32_node06_esp32_node06_*` | ESPHome node 06 |
| Master Bath | `sensor.mwave_masterbath_sink_*` | humidity drives the shower detector — see §8 |
| Office | `sensor.mwave_office_*` | |
| Utility | none | |
| Hallway, Green Room, Laundry, Backroom, Sauna, Catio, Library, 2nd Hallway, Cattic | none | |

---

## 4. Presence coverage — and the blind spots

This is the table that matters. "Presence" = `binary_sensor.mwave_<room>_presence`
(occupancy). Absence of a sensor is **not** absence of a person.

### 4.1 Rooms WITH a presence sensor

| Room | mmWave presence entity | Extra |
|---|---|---|
| Bathroom (1st) | `binary_sensor.mwave_1stbath_presence` | |
| Basement | `binary_sensor.mwave_basement_presence` | + PIR `binary_sensor.pir_basement_occupancy` |
| Bedroom | `binary_sensor.mwave_bedroom_presence` | |
| Entry | `binary_sensor.mwave_entry_presence` | |
| Kitchen | `binary_sensor.mwave_kitchen_presence` | |
| Living Room | `binary_sensor.mwave_living_tv_presence` | |
| Master Bath | `binary_sensor.mwave_masterbath_sink_presence` | |
| Office | `binary_sensor.mwave_office_presence` | |

Other PIR: `binary_sensor.pir_dabrig_occupancy` (dab-rig station, Utility).

### 4.2 Rooms with NO presence sensor (blind spots)

**Library · 2nd Hallway · Hallway · Green Room · Laundry · Backroom · Sauna ·
Catio · Cattic · Utility**

Consequences to design around:

- **The Office → Attic route is unmonitored except at the Office end.**
  The Cattic (attic) has no sensor; the only approach the system can see is
  `mwave_office_presence`. *(user-provided: the Office is the only way through to
  the Cattic)* — so an attic trip presents as an **Office** event.
- **Every vertical transition is invisible.** No sensor on the stairs, in the
  Ground `hallway`, or in `2nd_hallway`. Floor changes must be *inferred* from
  the pair of room sensors either side (e.g. Kitchen ⇄ Office with ~seconds
  between) — and that inference is unreliable.
- **The Library and both Hallways are the most-used unmonitored spaces** — the
  night routine walks through them (see [routines.md](routines.md)).

---

## 5. Doors and contacts

| Contact | Entity | Notes |
|---|---|---|
| Bedroom door | `binary_sensor.bedroom_door` | Zigbee (SONOFF). Mount-fix history: hal-context §7 |
| Catio door | `binary_sensor.catio_door` | Laundry ↔ Catio lower deck |
| Sauna door | `binary_sensor.sauna_door` | Sauna ↔ narrow **1st Bath**; **the interior door that can block the cats.** The sauna has no light/switch — this contact is the instant signal there |
| **Refrigerator door** | `binary_sensor.refrigerator_door` | **appliance contact** (smart fridge), *not* part of the SONOFF rollout |
| Front door | *(none)* | **Ring only** — motion/ding + camera, no open/closed contact |
| Pocket door (Entry ↔ Kitchen) | *(none)* | slides into the wall; rests **closed** — see §2.7 |
| Entry ↔ Hallway door | *(none)* | **double hinged**, two ~20 in leaves; rests **closed**; the `entry` area has **no contact at all** — see §2.7 |

Deck/cat-door/window contacts beyond the above are still pending — full plan in
[zigbee-door-sensor-rollout.md](zigbee-door-sensor-rollout.md).

### 5.1 The refrigerator door is a better signal than it looks

`binary_sensor.refrigerator_door` (`device_class: door`) is a **discrete,
unambiguous, high-quality event** on the Ground floor in the Kitchen, and it
fires in short, distinctive bursts (2–6 s open, a few seconds apart when a person
is grazing):

```
2026-10-04  fridge-door opens (EDT)
06:04:27  06:37:43  06:42:54  07:11:28  07:16:23  07:17:08
07:20:29  07:20:41  07:21:45  07:24:19  08:09:03  08:09:33
```

It is **currently referenced by no automation at all** (`ha_search` →
`config_total_matches: 0`). *(user-provided: "insulin is in the fridge downstairs
in the kitchen" — this contact is the cleanest machine-detectable marker of Matt's
wakeup step 2; see [routines.md](routines.md).)*

> Caveat: the fridge's *other* entities are stale —
> `number.refrigerator_fridge_temperature` last changed **2026-09-23**. The **door**
> contact is live and reporting; do not assume the rest of that device is.

---

## 6. Entity-naming traps (read before touching the powerstrips)

The entity names contain two collisions that have already caused one
misdiagnosis. Check the **device**, not the name.

### 6.1 Two different devices share the `tl_usb_4way_powerstrip` object-id prefix

| Entity | Friendly name | Actual device | Area |
|---|---|---|---|
| `light.tl_usb_4way_powerstrip_outlet_1` | "Attic Ladder" | *older powerstrip* | — |
| `light.tl_usb_4way_powerstrip_outlet_2` | "attic lights west" | *older powerstrip* | — |
| `light.tl_usb_4way_powerstrip_outlet_3` | "attic lights east" | *older powerstrip* | — |
| `switch.tl_usb_4way_powerstrip_outlet_1` | "sink light" | `tl.USB 4way powerstrip` (Tuya local) | `master_bath` |
| `switch.tl_usb_4way_powerstrip_outlet_2` | "main lights" | `tl.USB 4way powerstrip` (Tuya local) | `master_bath` |
| `light.tl_usb_4way_powerstrip_outlet_1_2` | "main lights" | **`switch_as_x` wrapper of the switch above** | `master_bath` |
| `light.tl_usb_4way_powerstrip_outlet_2_2` | "sink lights" | **`switch_as_x` wrapper of `switch…outlet_1`** | `master_bath` |

The `_2` suffix is HA de-duplicating an object-id clash. **`…outlet_1` and
`…outlet_1_2` are different physical outlets on different devices.**

### 6.2 `switch_as_x` shadow entities

The master-bath powerstrip exposes the same outlet twice — once as `switch.<x>`
and once as `light.<x>_2` via the **Switch as X** helper. Turning on the `switch`
moves the `light`; both are real, and a scene may reference either.

The relevant one for the morning chain:
`light.tl_usb_4way_powerstrip_outlet_1_2` ("main lights", master bath) is turned
**ON** by `matt-morning-macro-auto` at ~06:04 and **OFF** by `scene.daytime` at
~07:01. Verified in history. This is the outlet — *not* "Attic Ladder" — that the
morning chain toggles.

> Historical note: an earlier investigation attributed the 07:01 off-event to
> `light.tl_usb_4way_powerstrip_outlet_1` ("Attic Ladder"). History disproves it —
> that entity did not change state all morning. The correct entity is `…outlet_1_2`.

---

## 7. Route notes

*(user-provided unless stated otherwise)*

- **Office → Cattic** is the way up to the attic. The Office is therefore the
  only *visible* proxy for attic traffic, and a cat crossing the Office beam is
  indistinguishable from a person at the sensor level.
- **Matt does not walk *through* the Office** unless heading to the Cattic. He
  does legitimately **enter** the Office as part of the morning (routine step 9,
  "office/green room/kitchen/… is the daytime").
- **The morning has a Ground-floor kitchen leg.** Step 2 of Matt's wakeup is the
  fridge in the **downstairs Kitchen** (insulin) — so the morning crosses
  Second ⇄ Ground and back *before* the shower (see §8 and [routines.md](routines.md)).
- **Steve uses the Master Bath for clothes** (routine step 2) as well as the
  1st-floor Bathroom. The Master Bath is therefore **not** exclusively Matt's —
  any presence/humidity logic there is ambiguous between the two people.

---

## 8. Worked example: the 2026-10-04 morning, as the sensors saw it

Reconstructed from `ha_get_history` + automation `last_triggered`. Times EDT.
This is the reference timeline for debugging any "who was where" complaint.

| Time | Observation | Entity / automation |
|---|---|---|
| 06:00:00 | sleep model clears | `binary_sensor.bedroom_asleep` → off |
| 06:03:19 | Master Bath occupied | `mwave_masterbath_sink_presence` → on |
| **06:03:59.29** | **morning macro fires** — greeting + LBC radio; turns ON `switch…outlet_1` ("sink light") + `…outlet_2` ("main lights") | `automation.matt_morning_macro_auto` |
| 06:03:59.50 | same powerstrip turn-on re-triggers the greeting | `automation.matt_lights_bathroom` |
| **06:04:22.65** | **Kitchen occupied** ← *wakeup step 2 ("kitchen mwave sees me")* | `mwave_kitchen_presence` → on |
| 06:04:26.78 | Entry occupied | `mwave_entry_presence` → on |
| **06:04:27.08** | **fridge door OPEN** (3.3 s) ← *wakeup step 2 ("fridge door registers")* | `binary_sensor.refrigerator_door` |
| 06:04:59 | Kitchen clears | `mwave_kitchen_presence` → off |
| **06:12:39.52** | Master-bath humidity 62→**66** (crosses 65) → arms the shower flag | `automation.matt_shower_detected` → `input_boolean.matt_shower_done` = on |
| 06:37:39–06:48:40 | Kitchen + Entry activity; fridge opens 06:37:43, 06:42:54 | *(return-insulin / coffee leg)* |
| **07:01:34.66** | **Office occupied** | `mwave_office_presence` → on |
| **07:01:39.66** | 5 s dwell + flag armed → **`scene.daytime` applied** | `automation.matt_office_daytime_after_shower` |
| 07:01:39.69 | flag consumed | `input_boolean.matt_shower_done` → off |
| 07:01:39.84 | **`light.tl_usb_4way_powerstrip_outlet_1_2` ("main lights") ON → OFF** | *(the side effect)* |
| 07:01:50.70 | office plug ON (separate path) | `light.tl_office_emon_plug4` |
| 07:02:32–07:18:19 | Office pulses on/off a further 6× | `mwave_office_presence` |
| 07:11–07:24 | Kitchen; fridge opens 5× | `refrigerator_door` |
| 07:25:32 | Master-bath humidity 69→67 (settling) | `mwave_masterbath_sink_humidity` |

**How to read this:** the "office event" was **not** a 5-second blip — the sensor
held `on` for 58 s and pulsed for a further ~17 minutes. The automation fired
correctly at the 5 s mark. Whether *Matt* (or a cat, or a fan) tripped it is not
answerable from the sensors alone: the Cattic above the Office is unmonitored
(§4.2), and `person.matthew` read `home` continuously through the window. The two
weak links are the **flag** (armed by anonymous master-bath humidity — see
[routines.md](routines.md)) and the **over-broad `scene.daytime`** (§6.2).

---

## 9. Maintenance

Refresh this file when the entity registry changes materially — a new area, a new
presence sensor, a renamed contact. Reads to re-run:

1. `hal-mcp__ha_list_floors_areas` — floors, areas, per-area climate entities.
2. `hal-mcp__ha_search` with `domain_filter=binary_sensor` — presence/contact inventory.
3. `hal-mcp__ha_get_device` on any `mwave-*` / `pir-*` / powerstrip device — the
   canonical area + entity list (authoritative over friendly names).
