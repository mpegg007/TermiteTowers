<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: hams/docs/routines.md % -->
<!-- %ccm_git_object_id: hams/docs/routines.md@194 % -->
<!-- %ccm_git_commit_date: 2026-10-28 20:22:38 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: misc updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2026-10-05 mpegg house layout + routines docs -->
 <!-- %git_commit_history: 2026-09-25 mpegg  cleanup  -->
# Matt
## wakeup
1. leave bedroom after 5:30am door closed always
2. get insulin from fridge   ← fridge is DOWNSTAIRS, in the Ground-floor Kitchen
                                (observable: `binary_sensor.mwave_kitchen_presence`
                                 + `binary_sensor.refrigerator_door` open/close)
3. long bathroom shower      ← Master Bath; detected via sink-humidity > 65%
4. insulin shot
5. dress 
5.1 head downstairs
5.2 return insulin to fridge
5.3 head to living room where the shoes are
6. shoes on, wallet, 
6.1 head to entry 
6.2 hat on
6.3 door open/ring motion/door close
7. tims for coffee- front door, matt away, ring motion, front room mwave
8. kitchen breakfast make
9. living room eat, office/green room/kitchen/... is the daytime

##what i expect
1st entry to office turn on office lights, if no office motion for 1hr turn off, turn back on when enter office again.   night routine keeps office off until daytime trigger
stairs - by time i am awake stair lights bright morning yellow.   
steve up - stair lights daytime



##night
1. leave kitchen/living room
2. bathroom, brush teeth
3. leave bathroom
3. library cat treats - usually not 100% - involves entering bedroom door already open, getting cat treats , saying night to cat in library.
4. bedroom cat treats - usually - the other cat
5. tv - start watching
6. light turn off - trigger
7. fall asleep watching tv


# steve
## wakeup
1. leaves bedroom - often door closed but not 100%.
2. master bath clothes
3. 1st floor bath
4. living room tims coffee

---

## Matt wakeup — as observed (2026-10-04)

Sensor-derived reconstruction (EDT). Confirms the order above; the fridge step
happens **downstairs in the Kitchen**, and the return-to-fridge is ~33 min later,
after the shower.

| Step | Time | What the system saw |
|---|---|---|
| 1 | 06:00 | `binary_sensor.bedroom_asleep` → off |
| — | 06:03:19 | Master Bath occupied (`mwave_masterbath_sink_presence`) |
| — | 06:03:59 | **`matt-morning-macro-auto`**: greeting + LBC radio; turns ON master-bath powerstrip "sink light" + "main lights" |
| **2** | **06:04:22** | **Kitchen occupied** (`mwave_kitchen_presence`) → **fridge opens 06:04:27** (`refrigerator_door`) |
| 3 | 06:12:39 | Master-bath humidity 62→66 (>65) → `matt-shower-detected` arms `matt_shower_done` |
| 4–5 | 06:13–06:37 | shower runs; humidity peaks 72 |
| 5.1–5.2 | 06:37–06:43 | Kitchen again; **fridge opens 06:37:43 + 06:42:54** (insulin returned) |
| 6–7 | 06:45–06:48 | Entry + Kitchen activity (shoes/hat/door/coffee) |
| 9 | **07:01:34** | **Office occupied** → 07:01:39 `matt-office-daytime-after-shower` applies `scene.daytime` |

**The 07:01 "office" event is the *intended* trigger** — first Office entry after
the shower, routine step 9. The problem is not that it fired; it is **what it
fired** (see "known gaps").

## Known gaps / risks

> **Status 2026-10-18:** gaps 1, 2 and 4 are **fixed**; gap 3 is open, and gap 5 is
> **half-closed** — the greeting trigger is now debounced (45 s) but the sensor is still
> anonymous, and the owner deferred the "not Matt" gate. The 2026-10-15 fix introduced the
> **insulin-trip latch** — see §"The insulin-trip identity gate" below.

1. ~~**The shower flag is anonymous.**~~ **FIXED 2026-10-15.**
   `automation.matt_shower_detected` armed `input_boolean.matt_shower_done`
   purely on **master-bath humidity > 65%** between 05:00 and 09:00, with no
   identity check, so a Steve shower armed *Matt's* flag. It now also requires
   `input_boolean.matt_insulin_trip` (Matt's downstairs fridge grab), which makes
   the flag Matt's alone.
2. ~~**The flag stays armed for hours.**~~ **BOUNDED 2026-10-15.**
   The flag is still consumed by the *first* Office presence event after arming
   and re-armed at midnight, but the consumer
   (`automation.matt_office_daytime_after_shower`) now carries a **05:00–12:00**
   window, so a flag left armed in the morning can no longer apply `scene.daytime`
   in the evening. It can still be consumed by an early Office trigger — e.g. a cat
   heading to the Cattic (Office is the only visible approach) — so the *scene*
   itself remains the weak point (see gap 3).
3. **`scene.daytime` is over-broad.** It carries **14 entities**, including the
   master-bath 4-way powerstrip with an arbitrary per-outlet on/off pattern
   ("main lights" → **off**, "sink lights" → on, "Attic Ladder" → on, "attic
   lights" → off) plus duplicate `_2` shadow entities. Applying "daytime" today
   has side effects well beyond lights. See
   [house-layout.md §6](house-layout.md#6-entity-naming-traps-read-before-touching-the-powerstrips).
4. ~~**`refrigerator_door` is wired to nothing.**~~ **WIRED 2026-10-15.**
   Matt's step 2 signal is now consumed by `automation.matt-insulin-trip-arm`,
   which latches `input_boolean.matt_insulin_trip` on a fridge opening between
   04:30 and 09:00.

5. ~~**The 1st-bath morning greeting is anonymous — the mirror image of gap 1.**~~
   **DEBOUNCED 2026-10-18; identity still unresolved (by owner decision).**
   `automation.steve_morning_greeting` used to trigger on
   `binary_sensor.mwave_1stbath_presence` and announce **"Good morning Steve"**, but that
   sensor is an anonymous mmWave boolean with no identity signal (Z2M exposes no distance /
   angle / energy for the model). It is latched to **once per day**, so the **first** blip
   after 05:00 consumed it. On 2026-10-14 that first blip was a **53.6 s** event at
   **07:14:37** — followed by a 108 s gap — while the day's only clearly-real visit
   (**109 s** at 09:01:44) got nothing. The 1st Bath has **three openings** (Green Room barn
   door, sauna door, and the Backroom with **no door at all**), so through-traffic is
   unavoidable. The trigger is now
   `binary_sensor.mwave_1stbath_presence_confirmed` (45 s `delay_on`), so a walk-by no longer
   fires a greeting. Two consequences are deliberate, not regressions: a **45 s greeting lag**
   (you are greeted mid-routine, not on the threshold), and a real visit **shorter than 45 s**
   is now missed instead of greeted. The "not Matt" gate was **explicitly deferred** by the
   owner, so the identity half of this gap still stands — note HAL has **no `person.matt`**;
   `person.steve` is GPS/zone-level only, never room-level.

### Options to discuss

- ~~Gate `matt-office-daytime-after-shower` on the **fridge-door** event (Matt's
  insulin) in the same morning, or restrict the Office trigger to a tighter
  post-shower window.~~ **DONE 2026-10-15** — both, via the shared insulin-trip
  latch plus a 05:00–12:00 window (see below).
- Trim `scene.daytime` to lights only (drop the powerstrip outlets / `_2`
  shadows), so applying it cannot switch an outlet. **Still open — now the
  highest-value remaining fix**, because it is the side effect that makes a
  mistimed Office trigger visible.
- Give the Cattic/attic approach its own sensor so Office presence stops
  doubling as "someone is in the attic".

---

## The insulin-trip identity gate (2026-10-15)

The morning routines had no identity signal, so the *first* anonymous event of the
day won. On **2026-10-15** that meant Steve's bathroom break consumed
`input_boolean.matt_morning_macro_fired` (door 05:00:43 → sink 05:00:54.067, a
single 103 s burst; macro fired 05:00:54.070) and Matt's genuine 06:25:18 entry
got nothing. Steve's trip had **zero** kitchen/fridge activity.

Matt's step 2 — the insulin grab from the **downstairs** fridge — is the one
discrete, person-specific event both routines can share:

| Actor | Fridge before 09:00? |
|---|---|
| Matt (step 2 *is* an insulin grab) | always |
| Steve (bedroom → master bath clothes → 1st floor bath → out for coffee) | never observed |

**Components**

- `input_boolean.matt_insulin_trip` — the latch (helper, 9th `input_boolean`).
- `automation.matt-insulin-trip-arm` — arms it on
  `binary_sensor.refrigerator_door` → `on`, or on a **60 s sustained**
  `binary_sensor.mwave_kitchen_presence` dwell as a fallback for the LG Thinq
  **cloud** integration going unavailable. Window **04:30–09:00**.
- `automation.matt_morning_macro_reset` — clears it at midnight alongside the
  macro latch.

**Consumers** — both now require the latch to be `on`:
`matt-morning-macro-auto`, `matt-shower-detected`.

**Evidence the precondition does not delay a genuine Matt morning** — the fridge
has preceded the 65% humidity crossing on every morning checked:

| Date | Fridge opens | Humidity crosses 65% | Order |
|---|---|---|---|
| 2026-10-13 | 06:21:48 | 06:24:32 | fridge first |
| 2026-10-14 | 06:06:51 | 06:14:44 | fridge first |
| 2026-10-15 | 06:25:01 | 06:48:54 | fridge first |

**Known limitation (accepted):** the sink sensor is still anonymous. If Matt uses
the bathroom *before* his insulin grab — observed 2026-10-13 (sink 06:20:24, fridge
06:21:48) — the macro fires on his **second** sink entry instead of his first. That
delays the lights by a minute or two; it never misses. The macro window is
deliberately left at **05:00** rather than bumped to 05:30, because the fridge
gate, not the clock, is what discriminates.

**Residual risk:** the 60 s kitchen fallback is *not* person-specific — a
sustained kitchen visit by anyone between 04:30 and 09:00 arms the latch. If a
false arm is ever seen, delete the second trigger from `matt-insulin-trip-arm`;
the fridge trigger alone is the strong signal.

---

## Open: the master-bath speaker is offline (2026-10-15)

`media_player.bathroom_speaker` (Cast, `Lenovo CD-4N341Y`, **192.168.4.43:8009**)
has been `unavailable` since **2026-10-14 11:11:27**; the last successful cast was
2026-10-14 07:00:25.

This is **not** an HA-side fault. Verified 2026-10-15:

| Check | 192.168.4.43 (bathroom) | .34 / .35 (office / kitchen display) |
|---|---|---|
| ARP | `FAILED` / incomplete | `REACHABLE` |
| ICMP | 100% loss, "Destination Host Unreachable" | ok |
| TCP 8009 | "No route to host" | OPEN |

The device has **not** moved to a new IP (`watchyourlan.history` shows MAC
`9e:33:5f:bc:78:04` only ever at `.43`) and holds no Kea lease. It is powered off
or off Wi-Fi. The cast integration retries every 5 s and will self-heal when it
returns — nothing in Home Assistant can bring it back. Until then the morning
macro is **lights-only**.

Both automations that play to it (`matt-morning-macro-auto`,
`matt_lights_bathroom`) now set `continue_on_error: true` so a dead speaker cannot
abort the sequence.


