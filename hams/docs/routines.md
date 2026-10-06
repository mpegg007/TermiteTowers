<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: hams/docs/routines.md:172 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: 31e434d51d2b7f169149d73c13265bbc9100a12c % -->
<!-- %ccm_git_commit_id: 7ca87689c10da1e8ecebbe33bc2b42897f22b48c % -->
<!-- %ccm_git_commit_count: 172 % -->
<!-- %ccm_git_commit_date: 2026-10-05 20:46:08 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: house layout + routines docs % -->
<!-- %ccm_git_modify_date: 2026-10-05 20:46:09 % -->
<!-- %ccm_git_file_last_modified: 2026-10-05 20:21:08 % -->
<!-- %ccm_git_file_name: routines.md % -->
<!-- %ccm_git_path: hams/docs/routines.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: utf-8 % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 5862 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
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

1. **The shower flag is anonymous.** `automation.matt_shower_detected` arms
   `input_boolean.matt_shower_done` purely on **master-bath humidity > 65%**
   between 05:00 and 09:00. There is no identity check. Steve also uses the
   Master Bath (routine step 2, "master bath clothes"), so a Steve shower arms
   *Matt's* flag.
2. **The flag stays armed for hours.** It is consumed by the *first* Office
   presence event after arming, and only re-armed at midnight. So any Office
   trigger between the shower and 09:00 — including one caused by a cat heading
   to the Cattic (Office is the only visible approach) — will apply the scene.
3. **`scene.daytime` is over-broad.** It carries **14 entities**, including the
   master-bath 4-way powerstrip with an arbitrary per-outlet on/off pattern
   ("main lights" → **off**, "sink lights" → on, "Attic Ladder" → on, "attic
   lights" → off) plus duplicate `_2` shadow entities. Applying "daytime" today
   has side effects well beyond lights. See
   [house-layout.md §6](house-layout.md#6-entity-naming-traps-read-before-touching-the-powerstrips).
4. **`refrigerator_door` is wired to nothing.** Matt's step 2 has a clean,
   discrete, person-specific signal available and currently unused.

### Options to discuss

- Gate `matt-office-daytime-after-shower` on something better than anonymous
  humidity — e.g. require the **fridge-door** event (Matt's insulin) in the same
  morning, or restrict the Office trigger to a tighter post-shower window.
- Trim `scene.daytime` to lights only (drop the powerstrip outlets / `_2`
  shadows), so applying it cannot switch an outlet.
- Give the Cattic/attic approach its own sensor so Office presence stops
  doubling as "someone is in the attic".


